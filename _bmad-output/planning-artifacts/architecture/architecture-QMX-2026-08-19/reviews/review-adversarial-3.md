# Adversarial Review 3 — the indicator/structure increment (AD-22 … AD-25)

- **Target:** `ARCHITECTURE-SPINE.md` (status: final, updated 2026-08-20)
- **Scope:** AD-22 (indicator protocol), AD-23 (TA-Lib canonical arithmetic),
  AD-24 (light vs heavy), AD-25 (causal structure lifecycle) — and every place
  they touch AD-4, AD-7, AD-8, AD-10, AD-11, AD-12, AD-13, AD-15, AD-16, AD-17,
  AD-19, AD-21.
- **Prior passes:** `review-adversarial.md` (22 findings) and
  `review-adversarial-2.md` (22 findings) both ran *before* this increment
  existed — review 2 explicitly parked "indicator protocol shape, TA-Lib
  pinning, structure families" as later-sitting territory. **This increment has
  never been adversarially reviewed.** That is why the critical count is high;
  it is not a signal that the increment is worse than the rest of the spine,
  it is a signal that it is younger.
- **Date:** 2026-08-20

---

## 1. Method

I am not looking for things the spine forgot to say. I am building **pairs of
units one level down** — the concrete modules a factory agent would write from
these ADs — where *both* units obey every ratified clause to the letter, and
the two still cannot be assembled. Three shapes of failure count:

1. **Clashing shared-data shapes** — the same series, marker, or record
   expressed two incompatible ways.
2. **Two owners of one entity** — two packages each with the standing to mint
   or define the same thing.
3. **Conflicting state-mutation paths** — two legal answers to "who changes
   this, and does the change alter identity?"

Where the divergence is *loud* (a type error at tier 2) I rate it lower. Where
it is *silent* — two units that both run, both pass their own gates, and write
different numbers or different identities into permanent evidence — I rate it
critical. Evidence is append-only and fingerprints are forever; a silent
identity fork is the one class of bug this architecture cannot repair later.

**Verdict:** the increment's *rulings* are sound. Its *seams* are not yet
tight enough to hand to two agents working in parallel. Fourteen places will
produce divergent, conformant implementations, and eleven of those fourteen
contaminate identity or evidence rather than merely failing to compile.

Counts: **14 critical, 14 high, 8 medium (36 total).**

---

## 2. Critical — two conformant units WILL diverge

### C-01 — "identical outputs across modes" names no comparator, and the tier-1 matrix makes bit-equality unreachable

- **Unit A** (`tests/contract/test_mode_equality.py`, written by the batch
  team): AD-22 says outputs MUST be *identical*, so the test asserts
  `batch_out == stream_out` element-wise on the float64 payload. Exact. No
  tolerance. It cites AD-22 verbatim.
- **Unit B** (the same test, written by the streaming team): AD-23 says
  "Tolerances are declared per indicator — exact where possible, a stated float
  tolerance where cross-OS wobble is expected (AD-10)", so the test asserts
  `abs(batch - stream) <= declared_tolerance`. It cites AD-23 verbatim.

**Divergence.** Both readings are legal because AD-23's tolerance clause is
written for the *dual-reference* axis (TA-Lib version vs TA-Lib version) and
AD-22's equality law is written for the *mode* axis, and neither says whether
the tolerance crosses over. On any recursive indicator — EMA, MACD, RSI's
Wilder smoothing, ADX — a batch computation over the whole array and an
incremental streaming fold accumulate rounding in a different order and differ
in the last ulp *by construction*. Unit A's gate fails and blocks the merge;
Unit B's passes. Two factory runs, two verdicts, same code.

Worse, the law as written is **unsatisfiable on the ratified runtime matrix**.
AD-1 pins two tier-1 OSes. AD-10 states flatly that "cross-OS bit-identity of
float content is explicitly not promised." AD-4 tier 3 runs a clean-install
smoke on both OSes. So "identical" cannot mean bit-identical across the matrix,
yet nothing in AD-22 scopes the comparison to one machine, one build, or one
process. A conformance test that must pass on both OSes and must assert
bit-equality is a gate that can only be satisfied by luck.

**Closing clause (AD-22).** Replace "Identical canonical inputs MUST produce
identical outputs across modes" with: *the mode-equality law is a same-process,
same-build comparison against a per-indicator comparator declared in CT-16 and
expressed as an integer count of ULPs (default 0). Cross-OS and cross-build
agreement is never the mode-equality gate; it is a separate registered
comparison artifact under AD-23.* Also define "canonical inputs": the bulk-form
input series, its scale, its time axis, and the configured-indicator
fingerprint — nothing else.

---

### C-02 — the configured-indicator fingerprint is defined twice, and the two definitions disagree

- **Unit A** (`qmf.indicators._identity`): follows AD-10 — "every contract field
  is identity by default; display-only exclusion requires an explicit,
  versioned declaration in the contract — never an implementer's judgment
  call." It fingerprints the whole CT-16 configuration: formula, parameters,
  instrument, timeframe, **warm-up length, missing-value policy, declared state
  bound, light/heavy declaration, declared tolerance, arithmetic-reference
  pin**.
- **Unit B** (the node's instance pool): follows AD-22's own sentence —
  "Instances deduplicate by content fingerprint (formula + parameters +
  instrument + timeframe)". Four fields. Exactly as written.

**Divergence.** These are different hashes over the same object. Concretely:
two bots ask for EMA(20) on EURUSD H1, one configured to refuse on missing
input and one configured to emit gaps. Unit B hands both bots **one shared
instance** — silently overriding one bot's declared missing-value policy. Unit
A mints **two instances** — and the operator's ratified scaling promise
("instance count scales with distinct configurations, not consumers") quietly
means something else than he was told.

Then the outputs land in evidence. Two instances that Unit B considers
identical produce byte-differing series under one fingerprint — AD-10's "true
collision (same hash, differing bytes) is refused and alarmed". The dedup rule
manufactures the exact collision the fingerprint rule exists to detect.

Note also that AD-22's four-tuple is an *implicit exclusion list*, which AD-10
prohibits by name ("never an implementer's judgment call"). The increment
breaks an older AD's construction rule while quoting it.

**Closing clause (AD-22).** Delete the parenthetical four-tuple. Replace with:
*CT-16 declares its identity field set explicitly and versioned per AD-10;
that declared set is the configured-indicator fingerprint and is the only
dedup key. It includes at minimum formula identity, parameters, instrument,
timeframe, warm-up, missing-value policy, and the arithmetic-reference pin.*

---

### C-03 — warm-up is an identity field with no unit, and its value depends on the mode it was measured in

- **Unit A** (batch, wrapping TA-Lib): declares `warm_up = 19` for EMA(20) —
  TA-Lib's own lookback, the number of leading positions the reference cannot
  fill. Correct, checkable, derived from the canonical reference AD-23 pins.
- **Unit B** (streaming, QMX-owned): declares `warm_up = 100` for EMA(20) —
  five periods, the length its recursive seed needs before it agrees with the
  batch reference to within tolerance. Also correct: below that, the streaming
  instance is *not ready* in the plain sense of the word.

**Divergence, three ways.**

1. **Identity forks by mode.** AD-22 puts warm-up in the fingerprint. One
   configured indicator now has two fingerprints depending on which team's
   number was declared — and AD-22 in the same breath requires the two modes to
   be one contract.
2. **The equality law is evaluated on different regions.** Positions 19–99 are
   real numbers under Unit A and not-ready markers under Unit B. That region is
   precisely where recursive and batch arithmetic disagree most. The gate
   compares numbers to markers.
3. **No unit of measure.** "Warm-up length" is a bare number. Bars? Ticks? An
   AD-8 `Duration` in ns? All three are defensible; AD-8 makes `Duration`
   freely storable, which invites the ns reading. Then AD-25 says warm-up
   "with the confirmation delay feeds future split purge/embargo widths" —
   arithmetic that cannot add a bar count to a nanosecond duration. Two units,
   two embargo widths, two split manifests, two fingerprints for one dataset.

**Closing clause (AD-22).** *Warm-up length is an integer count of completed
input observations at the configured timeframe — never ticks, never a
`Duration`. It is a single value per configured indicator, identical in both
modes; where the arithmetic reference defines a lookback, the declared warm-up
is at least that lookback. A streaming implementation that needs more
observations than the declared warm-up to meet the equality comparator is
non-conformant, not differently warmed.*

---

### C-04 — the arithmetic pin names versions, not builds — and TA-Lib's output-changing settings are process-global and outside identity

- **Unit A** (`qmf-indicators` built on the operator workstation): installs the
  PyPI `ta-lib` 0.7.1 wheel, which bundles its own compiled C library. It also
  calls nothing else — accepting TA-Lib's default unstable-period of 0 and
  default compatibility mode.
- **Unit B** (`qmf-indicators` built on the Ubuntu VPS): installs system
  `libta-lib` 0.7.1 from the distro and builds the 0.7.1 wrapper from source
  against it. It sets `set_compatibility(COMPATIBILITY_METASTOCK)` because a
  house EMA-seeding convention was agreed in a story ticket.

**Divergence.** Both declare "TA-Lib 0.7.1 + 0.7.1", exactly the pin AD-23
ratifies, and both are honest. But:

- Two different C builds — different compiler, different flags, different libm
  — produce different last-ulp results. AD-10 requires float payloads to carry
  "(OS, library-version) provenance"; `0.7.1` is the same string for both, so
  the provenance field *cannot distinguish the two builds it exists to
  distinguish*.
- TA-Lib's unstable-period and compatibility settings are **process-global
  mutable state that changes numeric output**. They are not parameters, they
  are not in the pin, and they are not in any fingerprint. Two processes at the
  same pin compute different numbers under the same identity.
- The same fact breaks AD-15. AD-15 says "purity binds the pure-computation
  libraries (core, indicators, structure)". A library whose arithmetic depends
  on a process-global setting another module may have mutated is not pure, and
  two indicators in one process cannot hold different settings.

AD-23's whole purpose — "silent arithmetic drift under dependency upgrades" —
is defeated by drift that needs no upgrade at all.

**Closing clause (AD-23).** *The pin is the lockfile-resolved artifact
(distribution filename + hash) for both the C library and the wrapper, not a
version string, and that artifact identity is what AD-10 float provenance
records. The arithmetic reference's global settings (unstable period,
compatibility mode) are declared identity fields of the CT-16 contract, fixed
at stated values, set once at import, and any runtime mutation is an
`invalid input` refusal.*

---

### C-05 — the increment consumes a bar, a tick, and a timeframe; qmf-core defines none of them

- **Unit A** (`qmf-indicators`): MACD, ATR and every OHLC indicator need a bar.
  Core has no bar type, so it defines `qmf.indicators.Bar(open, high, low,
  close, volume, instant)` — a frozen dataclass per AD-3. Legal: AD-2 names the
  shared nouns as "Venue, Account, Instrument, WriterId", and `Bar` is not on
  that list.
- **Unit B** (`qmf-structure`): a swing point is defined over highs and lows.
  It cannot import `qmf-indicators` (default-deny; AD-25 pins core-only), so it
  defines `qmf.structure.Candle(...)`. Equally legal, same reasoning.
- **Unit C** (`qmf-data`): reads Parquet OHLC and defines a third shape at its
  store boundary.

**Divergence.** Three definitions of the single most-used noun in the entire
increment, in three packages, none able to import the others, with no
conversion contract between them — and every one of them is an *input
fingerprint* under AD-12. The same EURUSD H1 bar has three fingerprints
depending on which package serialized it, so results computed by indicators and
results computed by structure over identical market history can never
deduplicate, never share lineage, and never be compared. This is AD-2's
"edge modules never define shared nouns" failing because its enumerated list
predates the packages that need the noun.

`Timeframe` is in the same position: AD-22 puts it in the instance dedup key
and nothing anywhere defines it.

**Closing clause (AD-2 + AD-22).** *Extend the shared-noun list: `Bar` (OHLC
with an interval and a timeframe), `Tick`/`Quote` (bid/ask with source
timestamp per AD-21), and `Timeframe` are defined in `qmf-core` alongside
Venue, Account, Instrument and WriterId. No other package may define them.*

---

### C-06 — a timeframe with no anchor and no calendar produces two different series under one fingerprint

- **Unit A** (the node's bar builder): builds H4 bars anchored to UTC midnight —
  00:00, 04:00, 08:00 UTC. The obvious choice for a framework whose every
  timestamp is UTC ns.
- **Unit B** (the research workspace's bar builder): builds H4 bars anchored to
  the forex market-hours calendar's 17:00 America/New_York rollover, because
  AD-8 says trading date derives only from a calendar and the session schedule
  is data.

**Divergence.** Same ticks, two different H4 series — different opens, different
closes, different highs. Feed both into EMA(20) and you get two different
numbers. Both instances carry the **same** configured-indicator fingerprint,
because "timeframe" in the dedup key is the string `H4` and the anchor is not
part of it. The node and the research workspace now believe they computed the
same thing and their evidence stores will silently merge on the same identity —
or trip AD-10's collision alarm with no diagnosable cause.

Note the second-order effect: `qmf-indicators` depends on `qmf-core` only, so
it has **no calendar**. It cannot even ask which anchor is correct. Yet AD-8
forbids consumers from assuming constant session/day length, which is exactly
what a calendar-free bar builder must assume.

**Closing clause (AD-22 + AD-2).** *`Timeframe` is `(duration, anchor rule,
calendar identity + version)`, defined in `qmf-core`; the calendar identity and
version are identity fields of the configured-indicator fingerprint and of
every bar series. An indicator receives its timeframe as data; it never derives
bar boundaries itself.*

---

### C-07 — the int64→float descale is unpinned, so the two modes diverge before any arithmetic happens

AD-22 routes exact int64+scale values into float arithmetic ("indicator
arithmetic runs on floats off the money path per AD-7's carve-out"). AD-7
pins the *return* path — "a float crossing back to Money/Price/Quantity passes
a named conversion boundary with an explicitly stated rounding mode" — and says
nothing about the outbound path.

- **Unit A** (batch): `values / (10 ** scale)` as a vectorised float division.
- **Unit B** (streaming): `float(v) * (10.0 ** -scale)` per element, because
  there is no array to vectorise.

**Divergence.** `x / 100000` and `x * 1e-5` are not the same float64 for a
large fraction of inputs — the reciprocal is itself inexact. So batch and
streaming disagree in the last ulp on **every single input value, before the
indicator formula runs**. The AD-22 equality law then measures a discrepancy
that has nothing to do with either implementation's arithmetic, and no
tolerance derived from the formula can predict it.

A second, sharper case: an int64 scaled price above 2^53 cannot be represented
exactly in float64. Unit A silently loses precision; Unit B refuses with
`invalid input` citing AD-7's "never an implicit rescale or rounding". Both
defensible, and one of them silently degrades exact evidence into approximate
evidence with no record that it happened.

**Closing clause (AD-7 + AD-22).** *The exact→analytic descale is a named
conversion boundary with one implementation in `qmf-core` (the AD-10
"one implementation" discipline applied to conversion): a pinned formula, a
stated rounding mode, and a refusal when the scaled integer exceeds float64's
exact-integer range. No package computes a descale except by calling it.*

---

### C-08 — the not-ready marker and the gap marker have no representation, and every obvious choice violates fp1

AD-22 mandates two markers — a not-ready value during warm-up and a marked
output gap on missing input — and mandates they are "never a number". AD-10's
`fp1` forbids nulls ("an absent value is an omitted key") and declares arrays
order-significant.

- **Unit A**: uses `NaN` in the float payload and `INT64_MIN` as the int
  sentinel. Dense arrays, positions preserved, no nulls anywhere. Conformant on
  its face.
- **Unit B**: omits the missing positions entirely — "an absent value is an
  omitted key" read literally — and ships an index array beside the values.
  Also conformant on its face.

**Divergence.** Three ways, all fatal:

1. Unit B's omission **shifts every index**, and `fp1` says arrays are
   order-significant. Position 40 in B's array is not position 40 in A's. Any
   consumer written against one reads the other's series wrong without erroring.
2. Unit A's `NaN` breaks the AD-22 equality law itself — `NaN != NaN`, so a
   mode-equality test comparing two warm-up prefixes fails no matter how correct
   both implementations are. And quiet-NaN bit payloads are not stable across
   platforms and libraries, so AD-10's mandated float-payload integrity
   checksum differs across the two tier-1 OSes for logically identical output.
3. Neither marker can enter an identity-bearing structure: `NaN` is a float,
   and AD-10 refuses floats in identity content.

There is also a third marker nobody has named — AD-25's invalidated object and
AD-22's gap and warm-up markers are three distinct "no value here" states with
different meanings, and a consumer must tell them apart.

**Closing clause (AD-22 + AD-10).** *Series carry a parallel, integer-encoded
presence map (one bit per position, packed into int64 words) with a declared
enum of absence reasons — `not_ready`, `gap`, `invalidated`. Positions are never
omitted and never shifted; sentinel values inside the value array and `NaN` as a
marker are both prohibited. Equality comparisons compare presence maps first and
values only at present positions.*

---

### C-09 — restored state is not in identity, and restoring across machines silently changes the numbers

AD-22: "Each instance declares its state bound and supports snapshot/restore so
restart re-warm never replays a day."

- **Unit A** (node restart path): treats the snapshot as internal
  implementation. After restore, results carry the same AD-12 label as results
  from a cold full-history run — same producer, same inputs, same range, same
  world.
- **Unit B** (audit-minded team): includes the snapshot's fingerprint as an
  input fingerprint on every result computed after restore, because the state
  *is* an input.

**Divergence.** Unit A is the AD-10 collision case in slow motion: an EMA
restored from a snapshot and an EMA replayed from the series head produce
*different floats* (different rounding history), under **identical labels** —
"same hash, differing bytes… refused and alarmed", with the alarm firing on a
node restart that everyone considers routine. Unit B avoids the collision but
forks identity instead: the same computation now has two labels depending on
whether the process happened to restart, so the dedup and merge behaviour AD-12
exists to guarantee stops working exactly when two sandboxes did the same work.

Two further holes:

- **No format version.** AD-5 requires every serialized contract to carry an
  integer format version. Is a snapshot a serialized contract? Unit A pickles
  it (legal — "everything else in the package is private"); Unit B stamps a
  version. A cross-release restore then either silently loads a stale state
  layout or refuses.
- **Cross-OS restore.** The ratified topology is a Windows workstation plus a
  Linux VPS. A snapshot is a bag of float accumulators, and AD-10 explicitly
  refuses to promise cross-OS float bit-identity. Restoring a workstation
  snapshot on the VPS resumes a numerically different series while claiming
  continuity — a silent, permanent, unattributable divergence in live evidence.

**Closing clause (AD-22).** *A state snapshot is a serialized contract under
AD-5 with its own format version, scoped to a declared (OS, arithmetic-reference
build) tuple; restoring into a different tuple is an `unavailable dependency`
refusal. A result computed from restored state carries the snapshot's
fingerprint as an input fingerprint, and the snapshot's own label records the
input range it consumed — so restored and replayed results are distinguishable,
not colliding.*

---

### C-10 — light vs heavy is currently unfalsifiable, machine-scoped, and identity-bearing at the same time

AD-24: light iff it declares AND benchmark-proves four bounds — (1) per-update
cost within the live-path latency rung, (2) bounded declared state size, (3)
bounded declared evidence window, (4) synchronous availability.

- **Unit A** (indicator author on the Windows workstation): declares EMA(20) on
  H1 `light`. Bound 1: measured 4 µs, inside the rung it recorded on its own
  hardware. Bounds 2 and 3: it declares 8 KB and 19 bars — both finite,
  therefore "bounded". Bound 4: it returns synchronously. Four for four.
- **Unit B** (the same configuration, benchmarked on the VPS): measures 60 µs
  against a rung recorded from the VPS baseline and classifies the same
  configuration `heavy`.

**Divergence.** AD-24 says "the declaration is contract surface", and AD-10 says
contract fields are identity by default. So **the same configured indicator has
two fingerprints on two machines** — the precise failure review 1 found as F-03
("two tier-1 operating systems, two fingerprints for one indicator"),
reintroduced by the new increment through a different door. AD-13 compounds it:
baselines are "scoped to a declared (OS, CPU-class) tuple", so a lightness
verdict is *inherently* machine-scoped while the fingerprint must be
machine-neutral.

And the rung itself does not exist. AD-13 defers all numeric budgets until first
measured baselines, and the Deferred table repeats it. So today, bound 1 has no
threshold, and bounds 2 and 3 have no ceiling — "bounded" is satisfied by any
finite declared number, including a 5,000-bar warm-up and 40 MB of state. Bound
4 is an architectural property, not a measurement. **Three of four bounds are
self-certifying and the fourth's threshold is deferred**, so "benchmark-proves"
currently proves nothing and two units classify the same configuration
oppositely while both passing the merge gate.

**Closing clause (AD-24).** *The light/heavy classification is a declared budget
plus a machine-scoped verdict recorded as an AD-13 benchmark artifact — it is
declared display-only for fingerprint purposes and never enters the configured
indicator's identity. Until the live-path latency rung has a recorded baseline,
every configuration is `heavy` by default and a `light` claim is refused at the
gate. Bounds 2 and 3 carry stated ceilings in the CT-16 contract, not merely
declared values.*

---

### C-11 — AD-12's label carries the producer's *version* but not the producer's *identity*, and the increment is the first thing to create hundreds of producers

AD-12: "Every result carries: producer contract format version …, input
fingerprints, evidence time range, computation/occurrence identity, and world.
Together these are its identity."

- **Unit A**: reads "producer contract format version" as exactly that — an
  integer — and puts the configured-indicator fingerprint into **input
  fingerprints** (the configuration is an input).
- **Unit B**: reads inputs as the *market data* inputs only, and lets "producer"
  be implied by which module wrote the record.

**Divergence.** Under Unit B, `EMA(20)` and `SMA(20)` over the same EURUSD H1
range, in the same world, both at CT-16 format version 1, produce **byte-for-byte
identical labels**. AD-12's stated purpose — "prevents two computations sharing
a label" — fails on its first real test, because before this increment there
were only a handful of producers and now there is one per configuration. Two
different results deduplicate into one, or collide and alarm. Unit A is right,
but nothing in the spine makes it right.

**Closing clause (AD-12).** *Add a label part: **producer contract identity** —
the fingerprint of the configured producer (the CT-16 configured indicator, the
CT-17 configured family), distinct from the producer contract format version.
Identity = producer identity + producer format version + input fingerprints +
evidence range + evidence class + world.*

---

### C-12 — the structure lifecycle is a mutable state machine sitting on an immutable, content-addressed store

AD-25: "Every structure output carries observed-at and confirmed-at …;
invalidation appends invalidated-at, never deletes."
AD-16: "Lineage that accrues after birth … lives **exclusively** in append-only
typed edge records referencing fingerprints", and a record's stable id is
derived from its `fp1` fingerprint.

- **Unit A**: mints one record per structure object, with three time fields,
  writing `confirmed_at` when confirmation happens and appending
  `invalidated_at` later. This is what AD-25 literally describes.
- **Unit B**: mints an immutable record at observation and adds a `confirmed`
  edge and an `invalidated` edge later. This is what AD-16 literally requires.

**Divergence.** Unit A **mutates a content-addressed record after birth** —
which changes its fingerprint, which changes its stable id, which orphans every
lineage edge pointing at it, and which is a rewrite of evidence in a system
whose entire premise is that evidence is never rewritten. Unit B is
structurally sound but then AD-25's sentence "every structure output carries
observed-at and confirmed-at" is false: a reader holding the record alone cannot
tell whether the level is confirmed or dead. The two units produce different
record counts per object (1 vs 3), different identities, and different answers
to the only question a consumer ever asks — *is this level still valid at time
T?*

There is a timing impossibility underneath: `confirmed-at` is by definition
unknown at observation time. A single immutable record cannot carry a fact that
does not exist yet.

**Closing clause (AD-25).** *A structure object is minted once, at observation,
carrying observed-at, its family identity, and its declared confirmation rule.
Confirmation and invalidation are typed AD-16 edge records carrying their own
instants and referencing the object's fingerprint. "Confirmed" and "invalidated"
are read-time derivations over edges, never fields written into an existing
record. CT-17 states the read-resolution rule.*

---

### C-13 — the unconfirmed evidence class has nowhere to live in the label, so "never silently mixed" is unenforceable

AD-25: "Evidence consumed as confirmed uses confirmed-at; unconfirmed outputs
are a separately-labeled evidence class, never silently mixed."
AD-12's label has five parts. None of them is an evidence class.

- **Unit A**: implements the class as a distinct producer contract — an
  `unconfirmed` CT-17 variant with its own contract format version.
- **Unit B**: implements it as a boolean field in the record body, and filters
  at read time.

**Divergence.** Under Unit B the two classes have **identical labels**: same
producer, same inputs, same evidence range, same world — a confirmed swing and
its earlier unconfirmed emission are the same computation by AD-12's definition,
with different bytes. That is AD-10's true-collision alarm firing on correct
behaviour, or worse, a silent merge that hands a scalper's provisional object to
a research split as confirmed evidence. Under Unit A the two classes are
different *computations*, so a confirmed object can never be linked to the
unconfirmed one it grew from without inventing an edge type nobody ratified, and
they cannot be compared or superseded.

Note that AD-12 gives worlds a *storage* separation ("Identity distinctness
alone does not deliver world separation — storage separation does") and gives
evidence classes nothing at all. "Never silently mixed" has no enforcement
point.

**Closing clause (AD-12 + AD-25).** *Evidence class (`confirmed` /
`unconfirmed`) is a declared identity field of CT-17 and a named part of the
AD-12 label. An unconfirmed output and its later confirmed counterpart are
linked by a typed `confirmed-as` edge. Reads that request confirmed evidence
refuse unconfirmed rows with a `policy rejection` rather than filtering
silently.*

---

### C-14 — nothing says which instant partitions a structure record into a split, so look-ahead crosses the seal

AD-21: split manifests are "time-ordered, non-overlapping", boundaries are
"explicit stored TradingDates or instants", and the 12-month seal is enforced as
a refusal at every read boundary. AD-25 gives every structure object *two*
instants and defers the embargo width ("feeds **future** split purge/embargo
widths").

- **Unit A**: partitions structure records by **observed-at** — "when it
  happened" is the event time, and AD-19's bitemporal law says external facts
  carry event-time.
- **Unit B**: partitions by **confirmed-at** — AD-25 says evidence consumed as
  confirmed uses confirmed-at.

**Divergence.** Under Unit A, a swing point observed three bars before the split
boundary but confirmed two bars *after* it lands in the training partition
carrying information that only existed after the boundary. That is textbook
look-ahead, silently, inside the mechanism whose stated purpose is "prevents
research quietly consuming its own exam questions". Unit B is safe but produces
a different, incompatible manifest for the same history — different rows,
different manifest fingerprint, so the two workspaces' splits can never be
reconciled or compared.

This is live *now*: AD-21's seal is enforced today (review 2's N-04 fix), while
AD-25's embargo width is explicitly future work. The gap between those two
dates is where the leak sits.

**Closing clause (AD-21 + AD-25).** *Governed records are partitioned into
splits by knowledge time — confirmed-at for structure, the last input
observation for indicators. A manifest refuses any record whose observed-at
precedes a boundary while its confirmed-at follows it, unless the manifest's
declared embargo width covers the gap. The embargo width is a required manifest
field now, defaulting to the maximum declared confirmation delay plus warm-up of
every producer cited by the split.*

---

## 3. High

### H-01 — the bulk series form cannot be stdlib-only, immutable, and copy-free at once; three carriers, three byte layouts

AD-22 puts the bulk form in `qmf-core`, which AD-6 pins to zero dependencies.
The stdlib candidates are `array.array('q')`, `memoryview` over `bytes`, and
`list[int]`.

- **Unit A** (core): picks `array.array('q')` — the natural stdlib int64 array.
  It is **mutable**, so AD-15's "QMF values are immutable (safe to share by
  construction)" and AD-3's frozen-dataclass rule are both false for the most
  widely shared object in the framework; a caller can mutate a series after it
  has been fingerprinted.
- **Unit B** (`qmf-indicators`): TA-Lib's wrapper requires float64 **numpy**
  arrays, so it converts on entry and treats numpy as the working form.
- **Unit C** (`qmf-data`): reads Parquet through pyarrow and hands back a
  `pa.Int64Array`, arguing it *is* "int64 arrays plus out-of-band scale" and
  therefore satisfies the form.

**Divergence.** "One representation workspace-wide" has three implementations.
Interop is a copy at every seam (AD-13 makes peak memory a gate — three
simultaneous copies of a long series is a budget item nobody costed), and the
three carriers have **three different byte layouts**: `array.array` is a bare
native-order buffer, pyarrow adds validity bitmaps and offsets, numpy adds
strides. AD-10 requires float payloads to carry an integrity checksum; two units
checksumming "the same series" over their own carrier's memory produce different
digests forever.

**Closing clause (AD-22).** *Pin the carrier: the bulk form is a frozen value
holding a read-only `memoryview` over immutable `bytes`, little-endian int64,
plus an explicit length, the out-of-band scale, and the time axis. Checksums and
serialization are defined over exactly that byte layout. Conversions to numpy or
Arrow are private implementation details inside the consuming package and never
cross a public boundary.*

### H-02 — a scale change mid-history has no representation, and three legal handlings give three input fingerprints

AD-7 permits per-instrument scales and mixed-scale promotion; venues change
`digits` over time; the bulk form carries **one** out-of-band scale.

- **Unit A** promotes the whole series to the finest scale (every int64 value
  changes; logical prices do not).
- **Unit B** refuses the series with `invalid input` citing "never an implicit
  rescale".
- **Unit C** stores segments at their native scales with a scale index.

**Divergence.** A and C compute the same numbers from the same market history
but produce **different input fingerprints**, so every downstream result label
differs — one computation wearing two identities, which AD-12 exists to prevent.
B cannot load the history at all. *Closing clause:* the bulk form declares a
single scale and an ingest-side promotion is a **named, lineage-bearing
derivation** (AD-5's re-derivation rule: a new artifact with an edge to the
original), never an in-place normalization.

### H-03 — output alignment is undefined, and TA-Lib's own convention is the trap

TA-Lib's C API returns a trimmed buffer plus `outBegIdx`; its Python wrapper
returns a full-length array with a NaN prefix.

- **Unit A** (batch) returns the trimmed series plus a begin-index, faithful to
  the C reference.
- **Unit B** (streaming) emits one marked not-ready value per update, producing
  a full-length series.

**Divergence.** The equality law compares arrays of different lengths at
different offsets, and `fp1`'s order-significant arrays mean the two fingerprint
differently for arithmetically identical work. *Closing clause:* outputs are
always full-length and index-aligned to the input series; warm-up positions
carry the not-ready marker (C-08's presence map); begin-index trimming is
prohibited at the CT-16 boundary.

### H-04 — the streaming instance's object model: pure fold or mutable object

AD-15 declares `qmf-indicators` a **pure** library and exempts only "components
that own an external resource (stores, recorders, adapters)". A streaming
indicator owns no external resource and is nonetheless mutable state.

- **Unit A** builds `update(state, x) -> (state', out)` — an immutable fold,
  honouring purity, trivially shareable, snapshot = the state value.
- **Unit B** builds `instance.push(x)` mutating internal state — honouring "a
  stateful incremental instance" and making snapshot/restore meaningful.

**Divergence.** Two incompatible protocols under one contract; every consumer
package binds to one. Under B, "unlimited readers" means readers observe
whatever the feeder last pushed, with no way to know which input produced the
value they read — two readers on the same tick, two values, one evidence range.
*Closing clause:* name the stateful-instance class in AD-15's exemption
explicitly, pin one model (mutable instance with a one-feeder discipline is the
consistent choice given snapshot/restore), and require every streaming output to
carry the input sequence number that produced it.

### H-05 — instance dedup has no owner, and its only natural home is banned

AD-22 promises deduplication; AD-15 says the application owns all concurrency
and QMF spawns nothing.

- **Unit A** puts an instance pool inside `qmf-indicators` as a module-level
  registry — process-global mutable state in a library declared pure.
- **Unit B** leaves pooling to the application, so two bots each construct their
  own instance and dedup never happens — the operator's ratified scaling
  guarantee silently does not hold.

Neither unit dedups across processes (node and MIS are separate processes; the
workstation is a separate machine), so "two nodes mint two instances" is the
normal case with no rule covering it. *Closing clause:* CT-16 guarantees only
that *equal fingerprints imply substitutability*; instance pooling is
application-owned, `qmf-indicators` ships no global registry, and the spine
states plainly that dedup is per-process.

### H-06 — two owners of the same arithmetic

AD-23 binds "CT-16; qmf-indicators". It does not bind `qmf-structure`, and it
does not bind CT-16-conformant *extensions*.

- **Unit A** (`qmf-structure`, zone family): needs an ATR to size a zone. It
  cannot import `qmf-indicators` (default-deny), so it computes ATR inline —
  legally, since AD-23 does not reach it.
- **Unit B** (`qmf-indicators`): computes ATR by wrapping the pinned reference.

**Divergence.** Two ATRs, two numbers, both governed evidence, no rule broken.
The canonical-arithmetic ruling is defeated by the dependency rule that keeps
the two packages apart. Same hole for a custom CT-16 extension named `EMA`.
*Closing clause:* AD-23 binds **every producer of governed evidence**, not one
package; a structure family requiring indicator arithmetic consumes a CT-16
producer injected by the composition layer and never re-implements it.

### H-07 — the extension shape is called the primary use case and has no packaging, discovery, or namespace rule

AD-22 and AD-25 both make third-party authoring first-class ("family authoring
is the primary use case of the extension shape"). AD-2's only extension rule
covers **calendar** extensions.

- **Unit A** ships an indicator extension as another workspace package —
  colliding with AD-2's "seven packages" roster and its lockstep versioning.
- **Unit B** ships it as an installed entry-point discovered at import — which
  the Conventions table's banned vocabulary calls a "plugin", and which makes
  evidence non-rebuildable because nothing records which extension version
  produced an artifact.

*Closing clause:* extend AD-2's extension rule to indicator and structure
extensions — separate versioned packages outside the roster, on their own
ladder, whose distribution identity and version are declared identity fields of
every artifact they produce, with a stated discovery mechanism (explicit
registration by the composition root, not ambient scanning).

### H-08 — a declared float tolerance cannot enter a fingerprinted artifact

AD-23's dual-reference check is "a registered comparison artifact: input
fingerprint + parameter fingerprint + **declared tolerance** + verdict". AD-10
refuses floats in identity content.

- **Unit A** writes the tolerance as the string `"1e-9"`.
- **Unit B** writes `"0.000000001"`.

Both are strings, both legal under `fp1`, and the same comparison artifact gets
two fingerprints. A third unit tries to store `1e-9` as a number and is refused.
*Closing clause:* tolerances are declared as **integer ULP counts** (or a
scaled-integer mantissa/exponent pair), never decimal text, and the same
encoding is used by the C-01 mode-equality comparator.

### H-09 — an arithmetic-reference upgrade mints a version — of *what*?

AD-23: "any output change for identical canonical inputs mints a contract format
version (AD-5)". The pinned reference changed **four** indicators in 0.7.1.

- **Unit A** bumps CT-16's format version globally. Every indicator's label now
  carries a new producer version, so results for the ~200 *unchanged*
  indicators no longer deduplicate against their pre-upgrade selves.
- **Unit B** bumps a per-indicator contract format version for MACD, MACDFIX,
  TRIX and ULTOSC only — which requires per-indicator contracts that CT-16 does
  not describe.

*Closing clause:* the AD-5 format version that AD-23 mints is the **per-configured-indicator
contract** version, not the CT-16 protocol version; the arithmetic-reference
artifact pin is a declared identity field of that contract, so an
output-changing upgrade moves identity only for the indicators it changed.

### H-10 — structure and comparison artifacts have no writer, no sequence, no kind, and no journal event type

AD-25 routes emissions "via the application/composition layer"; AD-23 registers
comparison artifacts; neither package may touch `qmf-registry` or `qmf-data`.
Meanwhile AD-16 requires every record to carry writer + sequence, AD-21 requires
per-writer **gapless** sequences ("a gap signals loss") and pins **seven**
journal event types — none of which is a structure emission — and AD-16 reserves
kinds by name.

- **Unit A**: the application mints one WriterId and writes all structure output
  under it, so every family shares one sequence stream and one family's dropped
  record reads as another's loss.
- **Unit B**: `qmf-structure` takes a WriterId at construction and stamps
  records itself — putting a machine-scoped identity into a library declared
  pure, and into records that must deduplicate across machines.

*Closing clause:* name the emission path — structure objects and comparison
artifacts are **registry record kinds** (not journal events), minted by the
composition root, which holds the WriterId and owns the gapless sequence per
(writer, kind); the library returns fingerprintable content and never a stamped
record. Also correct AD-25's citation: it names CT-08, the promotion card
contract, which this spine does not even bind (see M-03).

### H-11 — confirmation delay is declared as a constant, but most real confirmation rules have unbounded delay

AD-25 makes the confirmation delay "declared contract surface entering the
fingerprint" and an input to embargo widths.

- **Unit A** (swing point, "N bars either side"): declares `delay = N` — a true
  constant.
- **Unit B** (structure break, "confirmed the moment price closes beyond the
  level"): the delay is event-driven and unbounded. It declares `0`, meaning
  "determined by the rule", and never refuses.

**Divergence.** A embargo computed from B's declaration is zero-width, so a
structure break confirmed weeks after the split boundary leaks straight into the
training partition. And the fingerprint differs for the same family depending on
whether the author read "delay" as *typical*, *maximum*, or *sentinel*.

Composition compounds it: AD-25 says warm-up and confirmation delay together
feed embargo width, but not whether they **sum**, **max**, or whether the
indicator's warm-up is already absorbed (a structure family cannot observe
anything while its input indicator emits not-ready markers). AD-17 composites
inherit the problem — a composite's declared delay is the sum of its children
under one unit and its own measured delay under another, so one logical object
gets two identities.

*Closing clause:* the declared value is a **maximum bound** (an integer count of
observations at the family's timeframe), with an `unbounded` variant that is
legal only for families excluded from split-governed evidence; embargo width is
the sum of the producer chain's declared bounds, stated once, and a composite
declares the sum of its children's bounds.

### H-12 — a fanned-out heavy value has no staleness stamp and nothing prevents it being called on the trading path

AD-24 sends heavy computation off the trading path, "computed once and fanned
out". AD-11 has a `stale evidence` category that nothing here uses.

- **Unit A**'s protocol exposes `classification` as a field the application may
  read or ignore; a bot calls a heavy configuration synchronously and blocks the
  live path — the exact thing AD-24 prevents.
- **Unit B**'s protocol refuses synchronous evaluation of a heavy configuration
  with `unsupported capability` — breaking every application written against A.

And neither stamps the fanned-out value with the input instant/sequence it was
computed from, so a bot cannot tell a fresh MIS value from an hour-old one.
*Closing clause:* a heavy configuration's synchronous entry point returns
`unsupported capability`; every fanned-out value carries the instant and input
sequence of its last input, and consuming a value older than a declared maximum
age is a `stale evidence` refusal.

### H-13 — "live in-memory use persists nothing" leaves journal decisions citing objects that do not exist

AD-25 binds the lifecycle law to governed evidence only. AD-21's journal records
`decision` events; AD-16 lineage references fingerprints.

- **Unit A**'s node uses in-memory structure and persists nothing, so a decision
  event references a level that was never stored — an unresolvable citation, and
  a decision that can never be replayed or audited.
- **Unit B** persists every structure object the moment it is cited.

*Closing clause:* any structure object cited by a journal event or a result
label is governed evidence by that act and must be persisted (or its full
fingerprint-bearing content inlined into the citing record). "Persists nothing"
applies only to objects nothing cites.

### H-14 — the granularity of streaming emission into evidence is undefined, and one reading defeats dedup entirely

- **Unit A** emits one evidence artifact per update; its AD-12 label's input
  fingerprints therefore change on every bar, so no two artifacts ever
  deduplicate and the artifact count grows without bound (AD-13's "artifact
  count" ladder is a load axis, not a budget).
- **Unit B** emits one series artifact per session or per day.

Two evidence stores with wildly different volumes, retention costs, and — more
importantly — different identities for the same computed history. *Closing
clause:* CT-16 declares the evidence emission granularity as contract surface
(per-window, with the window declared), and streaming updates are not
individually evidence-bearing.

---

## 4. Medium

- **M-01 — is dual-mode mandatory?** AD-22 says "one contract, two conformant
  modes" without saying every configuration must implement both. A heavy
  research aggregate has no sensible streaming form; a full-series normalisation
  cannot have one. Unit A ships batch-only and claims conformance; Unit B refuses
  it at the gate because the equality test cannot run. *Fix:* state that both
  modes are required for any configuration eligible for the live path, and that a
  batch-only configuration is `heavy` by definition and declares
  `streaming: unsupported`.
- **M-02 — the benchmark unit swings the classification by two orders of
  magnitude.** AD-22's rungs are "burst throughput and per-tick latency"; AD-24
  measures "per-update cost". For a bar-based indicator, ticks outnumber updates
  ~100:1 and most tick calls are no-ops. Unit A benchmarks per tick and looks
  fast; Unit B benchmarks per update and looks slow. *Fix:* define the rung's
  denominator as one *accepted input observation at the configured timeframe*,
  and measure the no-op tick path separately.
- **M-03 — AD-25 cites a contract this spine does not bind.** It routes
  structure emissions through "CT-06/07/08"; CT-08 is the promotion-card contract
  (AD-18) and is absent from the front-matter `binds` list. A unit could
  reasonably emit promotion cards from a structure family. *Fix:* cite the
  registry record contracts actually intended, and add CT-08 to `binds` or drop
  the reference.
- **M-04 — "everything else is private" leaves no way to obtain an indicator.**
  If only the CT-16 protocol and core value types are public, the concrete
  indicators are private and there is no named catalog or factory. Unit A exposes
  a public catalog (unnamed public surface); Unit B exposes a string-keyed
  lookup; extensions can register into one and not the other. *Fix:* name the
  discovery surface in AD-22 and make it the single registration point for
  extensions.
- **M-05 — nobody mints formula and family identities.** The dedup key says
  "formula"; AD-25 says families are versioned and addable. Neither says whether
  a formula/family is a name string or the fingerprint of its definition, nor who
  guarantees uniqueness once operator-authored families are first-class peers.
  AD-9's minting discipline (opaque, operator-minted, never reused) exists and is
  not applied here. *Fix:* apply AD-9's discipline to formula and family ids.
- **M-06 — `correlation_id` cannot cross a pure protocol.** AD-14 requires it
  "propagated across every package boundary". Unit A threads it through the CT-16
  call signature (contaminating a pure contract, and it must then be declared
  non-identity per AD-21's precedent); Unit B omits it and violates AD-14. *Fix:*
  state that pure-computation boundaries are exempt — correlation flows with the
  caller's context, not the value contract.
- **M-07 — are indicator instances and structure families "components"?** AD-14
  requires "every component exposes a no-argument `health()`". Unit A gives every
  streaming instance a `health()`; Unit B says only packages are components.
  *Fix:* define "component" for AD-14 as an owner of external resources or
  long-lived state — which pulls streaming instances in and pure batch functions
  out.
- **M-08 — an indicator in warm-up fails AD-24's fourth bound.** Bound 4 is
  "answer synchronously available on the trading path"; during warm-up the answer
  is a not-ready marker. Unit A treats a marker as an available answer (light);
  Unit B treats availability as "a number is available" (never light until warm).
  *Fix:* state that a marked not-ready value satisfies synchronous availability.

---

## 5. Attacks I declined

- Which indicators ship in the V1 catalog, and MIS fan-out wiring — Deferred
  table, node/documentation territory.
- The contents of the seed four structure families' confirmation rules — AD-25
  sets the bar ("precisely stated, X knowable at that instant") and each family
  is admitted individually.
- Numeric budgets themselves (AD-13 defers them). C-10 attacks the *dependency*
  of an identity-bearing declaration on a deferred number, not the deferral.
- Everything already found by reviews 1 and 2 and applied at desk. Where an old
  finding re-enters through the new increment (F-03's two-OS identity fork
  reappearing as C-10; the `fp1`-vs-real-data tension reappearing as C-08) I
  flagged it as new because the closing clause is different.
- Backtesting, venue, and risk territory (`world = simulated`, order state
  machine, Book internals).

---

## 6. What I would change first

Ranked by cost of getting it wrong, cheapest first:

1. **C-02** — delete AD-22's four-tuple parenthetical, one sentence. It
   currently contradicts AD-10's identity-by-default rule inside the same spine
   and mis-shares instances across incompatible configurations.
2. **C-05** — add `Bar`, `Tick`/`Quote` and `Timeframe` to AD-2's shared-noun
   list. One list edit today; three incompatible nouns in three packages
   otherwise, permanently, because those packages cannot import each other.
3. **C-01 + H-08** — scope the equality law to same-process/same-build and
   express its comparator (and AD-23's tolerances) in integer ULPs. This makes
   the increment's headline gate actually runnable on the ratified two-OS matrix.
4. **C-07 + C-08** — pin the descale and pin the marker encoding. These are the
   two data-shape decisions every indicator, every structure family, and every
   stored series depends on; both are cheap now and unfixable after evidence
   exists.
5. **C-10** — declare light/heavy *out of identity* and default everything to
   heavy until the AD-13 rung has a baseline. Otherwise the same indicator has a
   different fingerprint on the workstation and the VPS, which is the one failure
   this spine has already paid to fix once.
6. **C-12 + C-13** — pin the structure lifecycle onto AD-16's immutable
   record + edge model and give the evidence class a label slot. Without these
   the structure library either rewrites evidence or manufactures collisions on
   its first day.
7. **C-14** — state the split-partitioning instant now. AD-21's seal is enforced
   today while AD-25's embargo is deferred; that gap is an open look-ahead path
   into governed research evidence, and it is exactly the class of error the
   operator cannot detect after the fact.
8. **C-04** — pin the arithmetic reference by artifact hash and fix its global
   settings in the contract. "TA-Lib 0.7.1" is not a specification of a number.
9. **C-11** — add producer identity to the AD-12 label. It was harmless with
   five producers; the increment creates one producer per configuration.
