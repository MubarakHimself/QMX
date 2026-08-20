---
review: adversarial
target: ARCHITECTURE-SPINE.md (QMF V1 Foundation, draft 2026-08-19)
lens: two missions — (1) build-two-units-that-obey-and-still-clash; (2) operator-ordered contradiction sweep
scope: foundation primitives (AD-1..AD-14). Registry/data/venue/risk contract details are later sittings.
reviewer_stance: adversary. Every finding is an attack that succeeds against the spine AS WRITTEN.
date: 2026-08-19
---

# Adversarial review — QMF V1 Foundation spine

## Verdict

The spine is a strong, coherent piece of work and none of its rulings are *wrong* — but as a **build substrate it is not yet closed**: I constructed sixteen pairs of units, each obeying every AD to the letter, that still build incompatibly, and the operator-ordered sweep found five hard contradictions where two ratified clauses cannot both be honoured. Five findings are CRITICAL (two of them are flat self-contradictions *inside* the ratified text). The spine should not be handed to the factory until at least the CRITICAL tier is closed by new or tightened ADs.

**How to read this.** Mission 1 findings are written as *attacks*: two named units, the AD text each one hides behind, and the wreck that results. Mission 2 findings quote **the exact two clauses that conflict**. Each finding ends with a proposed AD fix, phrased tight enough to drop into the spine.

**Method note on scope discipline.** I discarded roughly a dozen candidate attacks that a later sitting will obviously rule on (order state machine, bar bid/mid basis, rate-limit chunking, store layout, promotion evidence, dedup policy for CT-10 observations *as a data-layer concern*). Those appear in §4 as notes, not findings. Everything in §2 and §3 is a hole in a primitive that is being **ratified today** and that a factory unit would have to interpret **this week**.

---

## 1. Tiered finding index

| # | Tier | Finding | Primary clauses |
|---|---|---|---|
| F-01 | **CRITICAL** | AD-8 forbids persisting monotonic time and simultaneously requires persisting it on every foreign event | AD-8 b4 vs AD-8 b7 |
| F-02 | **CRITICAL** | Journals are evidence (int64 ns) and journals are logs (ISO-8601 Z) — two ratified encodings for one record | AD-8 b1 vs AD-14 |
| F-03 | **CRITICAL** | AD-7 permits float analytics inside artifacts; AD-10 demands cross-machine hash equality. IEEE-754 does not deliver it, and "the money path" is never defined | AD-7 s3 vs AD-10 Prevents |
| F-04 | **CRITICAL** | `TradingDate` carries no calendar identity, and calendars are venue-parameterized while the prop-firm day boundary is per-account | AD-8 b2/b6 vs AD-8 b9 + AD-9 |
| F-05 | **CRITICAL** | AD-12's "producer contract version" is ambiguous across the two ladders AD-5 just minted; under lockstep it re-labels every result on unrelated releases | AD-12 vs AD-5 |
| F-06 | HIGH | AD-7's `precision` tag has no stated referent: venue wire scale, symbol digits, or broker `moneyDigits` | AD-7 vs cTrader encoding |
| F-07 | HIGH | AD-7 tags **Price** and **Quantity** with "currency" — meaningless for an FX quote, wrong for shares/lots | AD-7 vs inherited DEC-0015 |
| F-08 | HIGH | No verbatim-preservation rule for foreign **money**, though AD-8 mandates one for foreign **time** | AD-7 vs AD-8 b7 |
| F-09 | HIGH | AD-12 `world` and AD-9 account `role` are two overlapping enums that both contain "live"; paper accounts are unassignable | AD-12 vs AD-9 |
| F-10 | HIGH | `world = simulated` is not implementable without the parked sim-time machinery | AD-12 vs AD-8 b1 + Deferred |
| F-11 | HIGH | AD-10's "fixed encoding" and "display-only" are undefined — two conformant `fp1:` implementations disagree | AD-10 |
| F-12 | HIGH | "A collision on write is refused" breaks the ratified content-addressed sandbox-merge model | AD-10 vs kernel ruling |
| F-13 | HIGH | `Duration` is claimed by the monotonic clock and by `Interval` length — the exact "two incompatible duration types" the audit blocked | AD-8 b3 vs AD-8 b4 |
| F-14 | HIGH | "writer" is load-bearing in the ordering key but is never a defined noun; and no primary/dedup key exists once timestamps are banned | AD-8 b5 |
| F-15 | HIGH | The 17:00-NY rollover is stamped "verified" against research that marks it UNVERIFIED, in an AD that also says trust nothing from cTrader yet | AD-8 b6 vs AD-8 b7 vs research §2 |
| F-16 | HIGH | cTrader has **two** time authorities (17:00-NY day boundary and per-symbol `scheduleTimeZone`); a calendar supplies **one** rollover rule | AD-8 b6 vs research §2 |
| F-17 | HIGH | tzdata is pinned in the extension, but `zoneinfo` prefers the system tzdb — the fingerprint can record a version that was not used | AD-8 b6 vs AD-1 |
| F-18 | HIGH | AD-11 fixes the refusal *payload* but not the *mechanism*; value-type constructors cannot both raise and refuse | AD-11 vs AD-7 |
| F-19 | HIGH | Venue identity has no minting or stability rule, though symbol identity has both — white-label prop firms under cTrader are the stress case | AD-9 |
| F-20 | HIGH | AD-2's edge-module rule leaves Venue/Account/Instrument **records** with no owning package, forcing two owners | AD-2 vs AD-9 |
| F-21 | HIGH | One calendar instance per venue makes identical facts non-comparable across brokers, and migration re-labels derived evidence | AD-8 b6 vs AD-9 vs AD-12 |
| F-22 | HIGH | AD-12's run/occurrence id has no minting rule — random ids break merge, derived ids break occurrence counting | AD-12 |
| F-23 | MEDIUM | AD-5 lockstep vs "separately versioned" calendar extensions; a tzdata bump is either a format-version mint or a silent meaning change | AD-5 vs AD-2 vs AD-8 |
| F-24 | MEDIUM | Corrections are annotations, but no read-resolution rule exists; cross-writer annotation order is decided by writer-id sort | Conventions row 3 vs AD-8 b5 |
| F-25 | MEDIUM | `(instant, writer, sequence)` is deterministic, not causal — and the spine also says causality is instants-only | AD-8 b2 vs AD-8 b5 |
| F-26 | MEDIUM | AD-1 calls Ubuntu "CI-gated"; AD-4 defers CI until a remote exists. Today nothing is gated | AD-1 vs AD-4 |
| F-27 | MEDIUM | AD-13 bans invented numbers, then invents one; "significant regression" is undefined; baselines are not scoped to hardware/OS | AD-13 |
| F-28 | MEDIUM | int64-ns range, null sentinel, and overflow-checked arithmetic are unstated — `0` is a valid instant | AD-8 b1 vs AD-3 |

---

## 2. Mission 1 — the adversary's build

Rules of the game: I stand up two units one level below the spine. Each unit's lead is a competent engineer who has read every AD and obeys all of them. Neither cheats. They still cannot link.

### A-1 (F-01, CRITICAL) — `qmf-data` and `qmf-venue` disagree on whether a foreign event has three times or two

- **Unit A — the ingest team (`qmf-data`)** reads AD-8 bullet 4: *"Two clock kinds, type-separated: wall (meaning, storable) vs monotonic (durations, never persisted)."* "Never persisted" is absolute. Their `SourceObservation` record stores source-as-received + local receive **wall**. The monotonic reading is taken, used to compute an in-process latency, and discarded.
- **Unit B — the venue-adapter team (`qmf-venue`)** reads AD-8 bullet 7: *"Foreign timestamps are evidence: stored verbatim with declared zone/offset/resolution, plus local receive wall time and receive monotonic."* Their record has three time fields; the receive monotonic is an int64.
- **Both are literally correct.** The two bullets of the same AD say opposite things about the same field.
- **The wreck:** two record shapes for the same class of evidence, two fingerprints, and — worse — Unit A has *silently deleted the only wall-clock-step detector the DevOps audit identified* (`time-audit-devops.md`: "any step must be observable (wall-vs-monotonic divergence detector)"). Unit B has persisted an int64 that looks like a timestamp, is meaningless across reboots, and will be compared to another machine's monotonic value by the first person who writes a cross-machine latency chart.
- **Fix (new AD or AD-8 amendment):** state that a monotonic reading is **never a timestamp and never an instant**, but *is* storable as an opaque, boot-scoped correlation value that must carry a boot/epoch id, must never be compared across boot ids or machines, and must never be rendered as a time. That reconciles both bullets without weakening either.

### A-2 (F-02, CRITICAL) — the risk journal is written twice, in two encodings

- **Unit A — `qmf-risk`** treats the risk journal (CT-25) as evidence. AD-8: *"Every stored timestamp is int64 UTC nanoseconds since the Unix epoch"*, binding *"every stored record"*. Journal rows carry `ts_ns: int64` + per-writer sequence.
- **Unit B — the observability team** implements AD-14: *"Log/journal timestamps are UTC ISO-8601 with explicit Z."* Their journal writer emits ISO-8601 strings.
- **Both obey a ratified rule.** The collision is the word **journal**, which AD-14 uses for logs and which QMF already uses for a first-class evidence stream (CT-25 risk journal; the corpus's 12-stream journal).
- **The wreck:** one journal, two timestamp encodings; ISO-8601 at anything short of nanosecond precision **destroys the ns value AD-8 exists to protect**, and string timestamps cannot carry the per-writer sequence, so the merged journal loses its total order — the exact failure AD-8 bullet 5 was written to prevent.
- **Fix:** separate the two nouns explicitly. *Operator/diagnostic logs* → ISO-8601 Z. *Journals and any evidence stream* → int64 ns + writer + sequence, with ISO-8601 permitted **only as an additional display-only field excluded from identity** (which AD-10 then also has to be told about). Renaming AD-14's clause to "log timestamps" and adding "journals are evidence, not logs" closes it.

### A-3 (F-03, CRITICAL) — two tier-1 operating systems, two fingerprints for one indicator

- **Unit A — `qmf-indicators`** reads AD-7: *"Analytic float series are permitted outside the money path and are never monetary evidence."* It computes an EMA in float64 (numpy 2.5.2, per the Stack table), stores the series as a derived artifact, and fingerprints it per AD-10.
- **Unit B — the same package built and run on the other tier-1 OS** (AD-1: Windows 11 x86-64 **and** Ubuntu LTS x86-64, both tier-1). Different libm, possibly different BLAS, possibly different FMA contraction, and — if TA-Lib lands per the Stack table — a differently-compiled C library.
- **Both obey every AD.** Neither used a float on the money path.
- **The wreck:** AD-10's stated Prevents is *"the same object hashing differently across machines."* Float analytics inside a fingerprinted artifact deliver exactly that, and AD-4's tier-3 *"clean-install smoke on both tier-1 OSes"* is precisely where it detonates. Compounding: AD-10 says "fixed encoding" but never says how a float is encoded — Unit A serializes with shortest-round-trip `repr`, Unit B with `struct.pack('<d')`; `-0.0` vs `0.0` compare equal and hash differently; `NaN` is unorderable in a "sorted fields" canonicalization.
- **Second half of the same attack: "the money path" is never defined.** Unit A takes `Price` in, computes in float, returns float. Unit B (`qmf-risk`) multiplies that float by an account balance to produce a position size in `Money`. A float has entered the money path through a seam AD-7 does not police, and both units can point at AD-7's own sentence.
- **Fix:** (i) define "the money path" as a **taint rule**, not a location — any value that transitively contributes to an order quantity, price, P&L, or balance is on the money path regardless of which package computed it, and crossing back from float to Money requires a named, stated-mode rounding boundary; (ii) either ban floats from fingerprinted artifact **content**, or give AD-10 an explicit float canonicalization (IEEE-754 big-endian bytes, `-0.0` normalized, `NaN` refused) **and** a stated acceptance that float artifacts are reproducible only within a declared (OS, library-version) tuple that must then enter the fingerprint.

### A-4 (F-04, CRITICAL) — two units compute the same `TradingDate` and mean different days

- **Unit A — `qmf-risk`** models `TradingDate` as a bare `(year, month, day)` value object. It obeys AD-8: *"trading date derives only from a calendar, never from formatting an instant"* — a calendar **is** consulted at derivation time. Nothing in AD-8 says the resulting value must remember which calendar made it.
- **Unit B — `qmf-data`** models `TradingDate` as `(calendar_id, calendar_version, date)`, because AD-8 also says *"the calendar + tzdata version participates in every derived artifact's fingerprint."*
- **Both obey.** AD-8 defines `TradingDate` as core vocabulary but never states its **field set**.
- **The wreck:** Unit A's `TradingDate(2026, 8, 19)` derived under an ICMarkets calendar compares `==` to one derived under a Pepperstone calendar, or a crypto 24/7 calendar, or a prop firm's boundary. They name different 24-hour spans. Daily-loss aggregation, dataset splits (the audit's item 21), and bar identity all silently mix venues. Unit B's values never compare equal to Unit A's at all, so the two packages cannot exchange a trading date.
- **And now the operator's prop-firm case lands on top of it.** See F-04 in §3(b) — the same finding, viewed as a contradiction.
- **Fix:** make `TradingDate` a **compound value carrying its calendar identity and version in-band**, with equality defined only within one calendar identity and cross-calendar comparison returning a typed refusal (AD-11 category: invalid input).

### A-5 (F-05, CRITICAL) — two units stamp two different things as "producer contract version"

- **Unit A — `qmf-indicators`** reads AD-12 *"producer contract version"* alongside AD-5 ladder 1 (*"code packages use SemVer in lockstep"*) and stamps `qmf-indicators 0.4.2`.
- **Unit B — `qmf-structure`** reads the same phrase alongside AD-5 ladder 2 (*"Every serialized contract carries its own integer format version"*) and stamps `CT-16 v3`.
- **Both obey.** AD-5 mints exactly two ladders in one AD and AD-12 names neither.
- **The wreck:** Unit A's labels churn on **every unrelated release** — lockstep SemVer means a bugfix in `qmf-risk` bumps `qmf-indicators`, which re-labels every result that package ever produced. AD-12's own Prevents is *"two computations sharing a label, or one computation wearing two."* Unit A produces the second failure by construction. Meanwhile Unit A's and Unit B's results are not comparable in a merged ledger at all, because one field holds a SemVer string and the other an integer.
- **Fix:** state explicitly that the label's version field is the **serialized-contract format version (AD-5 ladder 2)**, that package SemVer never enters identity, and that the package version may be carried as a display-only provenance field excluded from the fingerprint.

### A-6 (F-06 + F-07 + F-08, HIGH) — three units, three scaled integers for one EURUSD price

- **Unit A — `qmf-venue`** takes cTrader's wire integer at face value. cTrader encodes prices as fixed-point `1/100000` regardless of the symbol's own `digits`. `Price(108234_0, precision=5)`.
- **Unit B — `qmf-data`** normalizes to the symbol's declared `digits` (5 for EURUSD, **3** for USDJPY), because AD-7 says *"tagged with currency and precision"* and the venue's declared precision is the natural referent. USDJPY 151.234 becomes `Price(151234, precision=3)` where Unit A holds `Price(15123400, precision=5)`.
- **Unit C — `qmf-risk`** picks one framework-wide scale (say 9dp) so that all arithmetic composes, which is the only reading under which AD-7's "smallest unit" is a single global thing.
- **All three obey AD-7 literally.** Every value is a whole-number count of a smallest unit, tagged with currency and precision, with no float anywhere.
- **The wreck (four ways):**
  1. **Arithmetic silently off by 100** the first time a JPY-pair price crosses the Unit A / Unit B seam, because both integers are "valid" and the precision tag is only checked if someone wrote the check.
  2. **Fingerprints diverge for the same economic fact.** AD-10 canonicalizes the stored fields; `(108234_0, 5)` and `(1082340000, 9)` are different bytes. AD-10's Prevents does not cover *this* — it prevents machines hashing one object differently, not two representations of one value. **There is no normalization rule before canonicalization.**
  3. **Money precision is a venue property, not a currency property.** cTrader carries a broker-configurable `moneyDigits`; two brokers can report USD balances at different scales. AD-7 ties precision to *currency*, so two `Money(USD)` values with different precision are legal and have **no stated combination rule** — and summing balances across ~6 brokers to get portfolio equity is a first-class operator requirement.
  4. **No verbatim rule for foreign money.** AD-8 bullet 7 gives foreign *timestamps* a full evidence discipline: stored verbatim, declared resolution, conversions derived with lineage, corrections as annotations. AD-7 gives foreign *money* nothing. Unit A stores only the converted value and can no longer reproduce the venue's own arithmetic when reconciling a fill; Unit B keeps the raw int + digits. Different record shapes, and only one of them can settle a dispute with a broker.
- **Also on AD-7's tag itself (F-07):** *"tagged with currency"* is coherent for `Money`, incoherent for `Price` (an FX quote is a ratio — USD per EUR; one currency tag names half of it), and wrong for `Quantity` (0.10 lots, 100 shares, 1.5 BTC are not currency amounts). The inherited invariant *"nouns must not preclude stocks/crypto"* (DEC-0015) is breached by the `Quantity`-carries-currency wording the day someone models a share count.
- **Fix:** (i) `precision` must name **whose** precision, and the rule must be one of "always the venue's declared symbol precision, stored alongside the raw venue-scale integer" or "a single framework scale with the venue scale preserved as evidence" — pick one, in the spine; (ii) mixed-precision arithmetic on the same currency is either auto-promoted to the finer scale (lossless only) or a typed refusal — never an implicit rescale; (iii) extend AD-8's foreign-evidence discipline to foreign money verbatim (raw integer + declared scale + declared digits + conversion lineage); (iv) re-word the tags: `Money(currency, precision)`, `Price(quote_currency, base_currency | unit, precision)`, `Quantity(unit, precision)` where `unit` is opaque and may be a currency, a lot, a share, or a coin.

### A-7 (F-09 + F-10, HIGH) — two units disagree on what world a paper account trades in

- **Unit A — `qmf-risk`** stamps `world = simulated` for a Book bound to a `paper-validation` account: no real money moves, so it is not the live world.
- **Unit B — `qmf-venue`** stamps `world = live`: a real venue, a real clock, real quotes, real (demo-server) fills, wall time advancing normally. `simulated` means synthetic data to them.
- **Both obey.** AD-12 lists the three members and defines none of them; AD-9 independently lists five account roles that include their own `live` and two paper flavours.
- **The wreck:** the operator's ratified position is that *"paper trading = standing state feeding alpha-decay sensing"* — paper results must be **comparable to live** results for decay detection. Unit A's labelling makes them a different world and therefore a different identity class; Unit B's makes them indistinguishable from live in a merged ledger. Either way alpha-decay comparison is built on sand, and the two enums (`world` and account `role`) both contain a member spelled "live" that means different things.
- **F-10, the operator's question (e), answered directly: the minimal label is implementable for `live` and `replay`, and NOT for `simulated`.** For `replay`, AD-8's data-driven injected clock returns genuine historical UTC instants — no parked machinery needed, the label is a pure tag. For `simulated` (synthetic ticks per L20/DEC-0054), there is **no real instant at all**, yet AD-8 bullet 1 says *"Every stored timestamp is int64 UTC nanoseconds since the Unix epoch"* with no world qualifier. A synthetic series either (a) claims fabricated UTC instants that are type-identical to real observations — the precise failure the parked `SimNanos`/`UtcNanos` split existed to prevent — or (b) cannot state an "evidence time range", which AD-12 makes mandatory. **So the third enum member is the part that needs the parked machinery.**
- **Second half:** AD-12's Prevents claims *"worlds mixing in merged ledgers"* is prevented. The Rule only makes worlds **identity-distinct** — two results with identical inputs in different worlds get different fingerprints and can then sit happily in the same table. Distinctness prevents *collision*, not *mixing*. The DevOps audit's actual rule ("replay may never write into the live evidence namespace") is a **storage** rule that AD-12 does not carry.
- **Fix:** (i) define each `world` member in one sentence each, and state the mapping from account role to world explicitly (recommend: paper/demo accounts are `world = live` because their time and quotes are real, with the account role carrying the money-reality; that keeps decay comparison honest); (ii) either drop `simulated` from V1 and mint it with the backtesting sitting, or state now that simulated runs stamp a distinct instant type / non-UTC time domain — do not leave a member that cannot be built; (iii) promote the namespace rule ("a non-live world may never write into the live evidence namespace") into the spine, since identity alone does not deliver the stated Prevents.

### A-8 (F-11 + F-12, HIGH) — two `fp1:` implementations, and a merge that refuses itself

- **Unit A — `qmf-registry`** implements AD-10's canonical serialization as sorted-key JSON with UTF-8 bytes. **Unit B — `qmf-data`** implements it as canonical CBOR. Both are *"one canonical serialization (sorted fields, fixed encoding)"*. Both emit `fp1:sha256:…` — because AD-10 says the prefix only advances on *"recipe upgrades"*, and neither team upgraded anything.
- **The wreck:** `fp1:` is self-describing about the *hash* and useless about the *recipe*. Two conformant implementations produce different fingerprints for one object while both claiming generation 1, which defeats AD-10's entire purpose. The same attack works on **"display-only fields excluded"**: AD-12 says human display names are outside identity, and nothing else is classified. Unit A calls AD-8's mandated *"each source's actual resolution"* metadata (display-only, excluded); Unit B calls it evidence (included). One observation, two fingerprints, both compliant.
- **F-12, a separate and sharper attack on the same AD:** *"A collision on write is refused and alarmed, never overwritten."* Unit A implements this literally — any write whose fingerprint already exists is refused. But the ratified kernel model is *"content-addressed Runs merge from many sandboxes into one ledger"* (kernel ruling 2026-08-17, echoed in AD-6's sandbox rationale): **identical artifacts arriving from two sandboxes are the normal case**, and Unit A refuses and alarms on every one of them. Unit B compares bytes first and refuses only on genuine same-hash-different-content. Both read AD-10 the same way; only one read the kernel ruling.
- **Fix:** (i) name the canonical encoding **exactly** (recommend a stdlib-implementable one, since AD-6 makes core zero-dep), specify integer/string/unicode-normalization/float/None handling, and state that the recipe — not just the hash — is what `fp1` versions; (ii) mandate that the fingerprint recipe has exactly one implementation, in `qmf-core`, and that no other package may re-implement it; (iii) give AD-10 a **field-classification rule** (identity by default; display-only requires an explicit declaration in the contract, and the declaration is itself versioned); (iv) split "collision" into *idempotent re-write* (same hash, byte-identical content → accept silently, it is the merge model working) and *true collision* (same hash, differing content → refuse and alarm).

### A-9 (F-13, HIGH) — two units invent two duration types, which is the thing the audit blocked

- **Unit A — `qmf-core`** reads AD-8 bullet 4 (*"monotonic (durations, never persisted)"*) as authoritative: `Duration` is what you get from subtracting two monotonic readings, and it is never stored.
- **Unit B — `qmf-structure`** needs the length of an `Interval` (AD-8 bullet 3: half-open, over instants) and the *"evidence time range"* AD-12 makes mandatory. Wall instants subtract to a span; that span is a `Duration (signed int64 ns)` per bullet 3, and it is persisted inside every result label.
- **Both obey.** Bullet 3 defines `Duration` as a core type with no clock affinity; bullet 4 assigns durations to the monotonic clock and forbids persisting them.
- **The wreck:** either `Duration` is one type used from both clocks (and then durations *are* persisted, contradicting bullet 4 and re-opening the wall-subtraction hazard the DevOps audit called a blocker), or Unit B mints a second span type (`EvidenceSpan`, `Tenor`, whatever) — which is **verbatim the architect audit's Blocker #2**: *"no Duration / half-open Interval types in core; Risk and node would each invent incompatible ones."* The spine adopted the type and then re-opened the hole from the other side.
- **Fix:** state that `Duration` is a pure quantity of nanoseconds with **no clock affinity**, that it is freely storable, and that the prohibition is narrower and belongs on the *operation*: **a duration used for latency, timeout, cooldown, or cadence must be measured monotonically; a duration derived from two wall instants is an evidence span and must never be used as an elapsed-time measurement.** Type-separate the *readings*, not the *quantity*.

### A-10 (F-14, HIGH) — two units define "writer" differently and the merged ledger has two orders

- **Unit A — the tick recorder** defines a writer as a **process instance**: a fresh UUID per boot, sequence restarting at 0. This satisfies AD-8's *"per-writer strictly-increasing sequence"* exactly.
- **Unit B — `qmf-venue`** defines a writer as a **logical stream** (`ctrader-icm-live-ticks`) whose sequence is durable across restarts.
- **Both obey.** AD-8 makes `writer` load-bearing in the ordering key and **never defines it as a noun** — while AD-9 goes to the trouble of making Venue and Account first-class.
- **The wreck:** (i) Unit A's ledger has an unbounded, growing writer set, so `(instant, writer, sequence)` gives a *different* total order after every restart, and replay reproducibility — which the DevOps audit says must follow "from stored fields alone" — depends on a UUID sort; (ii) after a crash-and-recover, the same ticks re-ingested under a new writer id are **not deduplicable**, and AD-8 has just banned the obvious key: *"timestamps are never primary or dedup keys"* — while **no AD states what the primary or dedup key actually is**. The foundation bans a key and supplies no replacement.
- **Fix:** make `WriterId` a first-class core noun with a stated minting rule (stable, durable, machine+role+stream scoped), require the boot/epoch id alongside it so a restart is visible without changing writer identity, and state the general identity rule for stored records — recommend: *the identity of a stored record is its AD-10 fingerprint; `(instant, writer, sequence)` is an ordering key, never an identity key.*

### A-11 (F-16, HIGH) — two units build the same venue calendar from two different venue clocks

- **Unit A — `qmf-data`** builds the forex calendar's session windows from the ratified rollover: 17:00 America/New_York, because AD-8 bullet 6 names it and the cTrader research confirms it is the platform-wide **daily bar boundary**.
- **Unit B — `qmf-venue`** builds session windows from cTrader's **per-symbol `scheduleTimeZone` trading intervals** (research finding 2, PRIMARY: *"Symbols carry their own `scheduleTimeZone` for trading intervals"*), because those are the venue's actual open/close facts.
- **Both are "venue-parameterized calendars implementing the core protocol."**
- **The wreck:** cTrader has **two** time authorities — a chart-day boundary in New York and a trading schedule in the symbol's own zone (cTrader-class servers commonly run EET/EEST, which the DevOps audit already flagged). AD-8 gives a calendar **one** rollover rule. Unit A's session windows and Unit B's session windows differ; every `TradingDate`, every session label, every weekend gap, every derived artifact's fingerprint follows the difference. And because F-04 means `TradingDate` carries no calendar identity, the divergence is **invisible at the type level**.
- **Fix:** a calendar must carry **two separate, separately-named facts**: an *accounting rollover* (which trading date an instant belongs to) and a *session schedule* (when the market is open), each with its own zone. One field named "rollover" cannot carry both.

### A-12 (F-17, HIGH) — same pinned tzdata, two different tz databases actually used

- **Unit A — `qmf-calendar-forex` on Ubuntu**, per AD-2/AD-8, pins the `tzdata` PyPI package and records its version in the fingerprint. But CPython's `zoneinfo` searches **system TZPATH first** and only falls back to the `tzdata` package. On Ubuntu the system tzdb wins. The recorded version is the pinned one; the consulted database is the OS's.
- **Unit B — the same package on Windows 11**, where there is no system tzdb, so the pinned `tzdata` is genuinely used.
- **Both obey every AD.** AD-8 requires *"the calendar + tzdata version participates in every derived artifact's fingerprint"* and the Stack table says tzdata is *"pinned in calendar extensions only"* — neither says the pinned copy must be the one resolved.
- **The wreck:** on AD-1's two tier-1 platforms, the same code with the same recorded tzdata version can resolve different historical offsets, producing different trading dates while the fingerprint asserts they came from the same tz data. The fingerprint becomes a **false attestation** — worse than no attestation. This is not theoretical: Ubuntu LTS ships a tzdb whose version drifts with system updates, which no lockfile controls.
- **Fix:** require calendar extensions to **force `TZPATH` to the pinned package** (`zoneinfo.reset_tzpath` to the wheel's data dir, or equivalent) and to **verify at import** that the resolved tzdb version equals the pinned one, refusing (AD-11: unavailable dependency) if not. State it in AD-8, not in an extension's README.

### A-13 (F-18, HIGH) — two units disagree on whether a refusal is returned or raised

- **Unit A — `qmf-core`** implements AD-11 as `Result[T, Refusal]` unions: no exception ever crosses a public boundary. `Money.try_create(...)` returns a refusal for an invalid amount; the constructor is private.
- **Unit B — `qmf-data`** raises `RefusalError(refusal)`. The refusal is still typed, still carries machine-readable context and retryability, and still is not prose. Their `Money(...)` constructor raises `ValueError` on an invalid amount — an ordinary Pythonic API, and AD-11 says it *"assumes nothing about node shape."*
- **Both obey.** AD-11 governs the **payload** and never the **mechanism**.
- **The wreck:** a consumer composing the two packages must simultaneously check unions and catch exceptions on every call; `pyright strict` (AD-3) validates both happily; and the two teams have shipped **two incompatible construction APIs for the same core value types** — because AD-11's `invalid input` category means a bad `Money` is a refusal, which means value-type constructors cannot be ordinary constructors, which changes every downstream signature in the framework. This is a foundation-wide API-shape fork decided by nobody.
- **Fix:** state the mechanism in AD-11: public boundaries **return** typed refusals; exceptions are reserved for programmer error and never carry refusals across a package boundary. Then state the value-type construction pattern once (private `__init__` + `try_create` returning a refusal, or an unchecked constructor plus a separate validating factory) so all seven packages build the same shape.

### A-14 (F-19 + F-20, HIGH) — two owners of Venue, two owners of Account

- **Unit A — `qmf-venue`** needs a `Venue` and an `Account` to talk to cTrader. AD-2's edge rule says *"nothing imports `qmf-venue` or `qmf-risk`"*, so whatever it defines is **unreachable by everyone else** — it must define its own.
- **Unit B — `qmf-risk`** needs an `Account` because AD-9 says *"Books bind to accounts"*. It is also an edge module, also unimportable. It defines its own.
- **Both obey.** AD-9 declares Venue and Account *"distinct first-class nouns"* and **assigns them to no package**; AD-2's edge rule guarantees that if either edge module owns them, the other cannot use them.
- **The wreck:** two `Account` types, two `Venue` types, two record shapes, two fingerprints, and an application (the trading node, outside QMF) forced to write a translation layer between two halves of its own framework — for the noun that binds a Book to real money.
- **F-19, the sharper half:** AD-9 gives **symbols** a full identity discipline (opaque, never parsed, renames never rewrite history) and gives **venues** nothing. What mints a venue id? Unit A derives it from the broker's cTrader identifiers; Unit B uses an operator-assigned slug. Now apply the operator's own scenario: **a prop firm under cTrader is a white-label of the same platform** — same infrastructure, same 17:00-NY boundary, same symbol names, different broker entity, different accounts, possibly different `moneyDigits` and symbol digits. Unit A calls it the same venue; Unit B calls it a different one. Instrument identity is `(venue, symbol)`, so **the two units disagree about whether two records describe the same instrument** — the single most load-bearing identity in the framework. And AD-9 says *"broker migration is normal"* without saying whether a rename, an acquisition, or a server migration mints a new venue.
- **Fix:** (i) place `Venue`, `Account`, and `Instrument` **nouns** in `qmf-core` (definitions only — consistent with L13) and their **records/lifecycle** in `qmf-registry`, stated explicitly in AD-2 or AD-9; (ii) give `VenueId` the same discipline symbols have: operator-minted, opaque, stable, never derived from a mutable broker attribute, never reused, with renames as dated alias records.

### A-15 (F-21, HIGH) — six brokers, six calendars, one market fact, six fingerprints

- **Unit A** mints a single `qmf-calendar-forex` instance and parameterizes it per venue, so all cTrader brokers sharing the 17:00-NY boundary resolve through one calendar identity.
- **Unit B** mints one calendar instance per venue, because AD-8 says calendars are *"venue-parameterized"* and the venue is the parameter.
- **Both obey.**
- **The wreck:** under Unit B, the identical bar from two brokers produces derived artifacts with different fingerprints (AD-8: calendar version participates in every derived fingerprint), so **the operator's explicit multi-broker programme — broker specialization, one broker for scalping, one for Asia pairs, pair splitting, cross-broker comparison — is non-comparable by construction**. And AD-9's *"broker migration = new venue + accounts, old evidence untouched"* holds for raw evidence but is **false for derived evidence**: a migration mints a new calendar identity, which re-fingerprints every indicator, every structure artifact, every result label from that point on, and nothing in the spine says whether pre-migration and post-migration artifacts are comparable.
- **Fix:** separate **calendar identity** (the rule set: "forex-17:00-NY-v3") from **calendar binding** (which venues use it). Venues that share a rule set share the identity, and only the rule set + tzdata version enter fingerprints. State explicitly that a venue change that does not change the rule set does not change derived-artifact identity.

### A-16 (F-22, HIGH) — random run ids and content-addressed merge cannot both be true

- **Unit A** mints `run_id` as a UUID4 per process run. **Unit B** derives it as a hash of `(input fingerprints, contract version, world, parameters)`.
- **Both obey.** AD-12 lists *"run/occurrence id"* and states no minting rule.
- **The wreck:** Unit A's ledger cannot recognise that two sandboxes computed the identical artifact — directly breaking the ratified kernel model (*"content-addressed Runs merge from many sandboxes into one ledger"*) and violating AD-12's own Prevents (*"one computation wearing two"* labels). Unit B's ledger cannot distinguish two genuinely separate live occurrences of the same computation at different times — violating the other half of the same Prevents. **The spine's Prevents clause demands both properties from one field.**
- **Fix:** split the field. A deterministic **computation identity** (content-derived, enables merge and dedup) and a separate **occurrence record** (when/where/by whom it was run, display/provenance, outside identity). AD-12 currently fuses them.

---

## 3. Mission 2 — operator-ordered contradiction sweep

Exact clause pairs. Quoted text is verbatim from the spine, the memlog, or `ctrader-time-research.md`.

### 3.0 — Internal contradictions found by cross-checking the thirteen rulings against each other

**C-1 (F-01, CRITICAL) — AD-8 against itself, on persisting monotonic time.**
> AD-8 bullet 4: *"Two clock kinds, type-separated: wall (meaning, storable) vs **monotonic** (durations, **never persisted**)."*
> AD-8 bullet 7: *"Foreign timestamps are evidence: stored verbatim with declared zone/offset/resolution, plus local receive wall time and **receive monotonic**."*

These cannot both hold. Bullet 7 mandates persisting exactly what bullet 4 forbids persisting. Resolution in A-1.

**C-2 (F-02, CRITICAL) — AD-8 against AD-14, on journal encoding.**
> AD-8 bullet 1: *"**Every stored timestamp** is int64 UTC nanoseconds since the Unix epoch"* — binding *"every package; **every stored record**"*.
> AD-14: *"**Log/journal** timestamps are UTC ISO-8601 with explicit Z."*

The risk journal (CT-25) is a stored evidence record and a journal. Resolution in A-2. The Consistency Conventions table reproduces both rules side by side (`Timestamps int64 UTC ns` and `logs UTC ISO-8601 Z`) without noticing the overlap.

**C-3 (F-13, HIGH) — AD-8 against itself, on who owns `Duration`.**
> AD-8 bullet 3: *"Core time vocabulary: Instant, CivilDate, TradingDate, **Duration (signed int64 ns)**, **Interval (half-open, contains/overlaps)**, SessionWindow."*
> AD-8 bullet 4: *"wall (meaning, storable) vs monotonic (**durations**, never persisted)."*

An `Interval` over wall instants has a length; AD-12 persists an *"evidence time range"*. Either durations are persisted or a second span type gets invented. Resolution in A-9.

**C-4 (F-03, CRITICAL) — AD-7 against AD-10, on floats in fingerprinted artifacts.**
> AD-7: *"**Analytic float series are permitted** outside the money path and are never monetary evidence."*
> AD-10 Prevents: *"the same object **hashing differently across machines**"*; Rule: *"one canonical serialization (sorted fields, **fixed encoding**…)"*.

AD-1 makes Windows **and** Ubuntu both tier-1. IEEE-754 results are not guaranteed bit-identical across platforms/libm/compiled-TA-Lib builds, and AD-10 states no float encoding. Resolution in A-3.

**C-5 (F-05, CRITICAL) — AD-12 against AD-5, on which version the label carries.**
> AD-12: *"every result carries **producer contract version**, input fingerprints, evidence time range, run/occurrence id, and world"*.
> AD-5: *"**code packages use SemVer in lockstep**… **Every serialized contract carries its own integer format version**"*.

Two ladders, one unqualified phrase. Under the first reading, an unrelated package release re-labels every result — which AD-12's Prevents forbids (*"one computation wearing two"*). Resolution in A-5.

**C-6 (F-25, MEDIUM) — the ordering key is deterministic but is not causal, and the spine uses it as both.**
> AD-8 bullet 2: *"**Causality is compared on instants only** — trading date is never a causality proxy."*
> AD-8 bullet 5: *"instants alone never totally order events… **tie-break is (instant, writer, sequence)**."*

For two events at the identical instant from different writers, the tie-break resolves order by **writer-id sort**, i.e. by a name. It is reproducible, but it is not causality. A registry unit building the look-ahead test (GAP-0016) will read the tie-break as an ordering fact and admit a same-instant input that instants-only would refuse. State explicitly that the tie-break is a **presentation/replay determinism device with no causal meaning**, and that causality tests must refuse rather than tie-break.

**C-7 (F-26, MEDIUM) — AD-1 claims a gate AD-4 defers.**
> AD-1: *"Tier-1 tested targets: Windows 11 x86-64 and Ubuntu LTS x86-64 (**CI-gated**)."*
> AD-4: *"Commands are host-neutral; **bind to GitHub Actions only when a remote exists**. Factory runs gates locally meanwhile."*

The operator's machine is Windows 11 with no remote. Today, "CI-gated Ubuntu" is unenforceable, and AD-4 tier-3's *"clean-install smoke on both tier-1 OSes"* cannot run. Not fatal — but AD-1 should say "CI-gated once a remote exists; until then the Ubuntu target is untested," or the factory will believe a gate exists that does not.

**C-8 (F-27, MEDIUM) — AD-13 against itself.**
> AD-13: *"**No invented performance numbers.**"*
> AD-13, same rule: *"One commitment now: `qmf-core` imports in **well under one second**."*

Also unresolved in AD-13: "significant regressions" is undefined (so the merge gate's threshold is per-agent judgement), and baselines are not scoped to hardware or OS — while AD-6's own rationale is *"factory agents in disposable sandboxes"* with varying CPU. A baseline recorded on a fast sandbox permanently blocks merges from slow ones. Fix: scope baselines to a declared `(os, cpu-class)` tuple, define "significant" as a stated multiple of measured run-to-run variance, and re-label the 1s import figure as an explicit **design constraint** (which it is) rather than a measurement.

**C-9 (F-23, MEDIUM) — AD-5 lockstep against AD-2's out-of-roster extensions.**
> AD-5: *"code packages use SemVer **in lockstep**"*.
> AD-2: *"Calendar extensions are **separate versioned packages outside the roster**, under the same workspace."*

Are workspace extensions in lockstep or not? And the sharper question AD-5 cannot answer: a tzdata refresh can retroactively change the local-time mapping of historical dates, therefore change a `TradingDate` derived for a past instant. AD-5 says *"a format version's meaning **never changes after the fact**"*. One unit treats a tzdata bump as a patch (meaning unchanged); another mints a new contract format version (meaning may have changed). Both defensible. Rule needed: **re-deriving a value under a newer calendar/tzdata version produces a new artifact with its own fingerprint and a lineage edge to the old one — never a rewrite, never a silent equality.**

**C-10 (F-24, MEDIUM) — the ns integer has no stated range, sentinel, or overflow rule.**
> AD-8 bullet 1: *"Every stored timestamp is **int64 UTC nanoseconds** since the Unix epoch (POSIX, no-leap-second semantics stated)."*
> AD-3: *"money/time exact-arithmetic primitives require **full coverage**."*

The architect audit item 17 asked for the range (1677–2262) to be stated once; the spine does not state it. Nor does it state a null representation — one unit will use `0`, which is a **valid instant** (1970-01-01T00:00:00Z) — nor require checked arithmetic on ns math (Python ints don't overflow, but the int64 storage boundary does). Small, cheap, and it will bite exactly once, expensively.

**C-11 (F-24b, MEDIUM) — corrections are annotations, with no read-resolution rule.**
> Conventions row 3: *"Evidence is append-only, **corrections are annotations**"*.
> AD-8 bullet 5: *"Every record stream carries a **per-writer** strictly-increasing sequence."*

Nothing states how a reader **resolves** an annotated record into current truth, and cross-writer annotation ordering falls back to writer-id sort (C-6). Two units — one folding `supersedes` chains inline, one joining a separate annotation stream — produce different "current" values from the same store. In-scope because both the append-only convention and the ordering key are ratified here, even though the store's shape is a data-sitting concern.

---

### 3(a) — Time model vs the multi-broker / multi-account model

**Finding (F-21, HIGH): calendar identity is bound to the venue, but ~6 venues share one rule set.**
> AD-8 bullet 6: *"**Market-hours calendars are venue-parameterized**, versioned extension packages… the **calendar + tzdata version participates in every derived artifact's fingerprint**."*
> AD-9: *"**Multi-broker (≈6 venues) and broker migration are normal, not special cases.**"*

If venue-parameterization means one calendar identity per venue, the same market fact yields different fingerprints per broker and cross-broker comparison — the operator's stated programme (broker specialization, Asia-pairs broker, pair splitting) — is impossible. If it means one shared identity with a venue parameter, then AD-9's *"broker migration = old evidence untouched"* holds for derived artifacts too. The spine does not choose. Resolution in A-15.

**Finding (F-09, HIGH): two enums, both containing "live".**
> AD-9: *"one venue may hold many accounts, each with a **role (live/demo/paper-validation/paper-benched/prop-firm)**"*.
> AD-12: *"…and **world (live / replay / simulated)**."*

Neither enum's members are defined against the other's. A `paper-validation` account is `world=live` to one unit and `world=simulated` to another, and the operator's ratified use of paper mode (*"paper trading = standing state feeding alpha-decay sensing"*) requires paper and live results to be comparable — which the two readings make either trivially true or impossible. Resolution in A-7.

**Finding (F-19, HIGH): venue identity has no rule, and account roles now depend on it.**
Covered in A-14. AD-9 protects symbol identity meticulously and leaves venue identity — the *first* element of the instrument tuple — completely unspecified, at the moment it declares ~6 venues normal.

**Non-finding (checked, no conflict):** `(venue, opaque symbol)` identity + a distinct Account noun genuinely does carry broker specialization, multi-pair splitting, and routing as node/Book concerns, exactly as the memlog concluded. That part holds.

---

### 3(b) — Time model vs prop-firm-under-cTrader

**Finding (F-04, CRITICAL) — this is the sharpest contradiction in the sitting.**
> AD-8 bullet 2: *"Civil date and trading date are distinct types; **trading date derives only from a calendar**, never from formatting an instant."*
> AD-8 bullet 6: *"**Market-hours calendars are venue-parameterized**…"*
> AD-8 bullet 9: *"…**prop-firm day boundaries evaluated in the prop firm's stated timezone**…"*
> AD-9: *"one venue may hold **many accounts**, each with a role (live/demo/paper-validation/paper-benched/**prop-firm**)."*

Follow the chain:
1. A prop-firm account sits **under a venue** (AD-9). Two accounts on the same venue — one live, one prop-firm — need **two different day boundaries**.
2. A calendar is parameterized **by venue** (AD-8). A venue-parameterized calendar structurally cannot express two boundaries for two accounts on one venue.
3. A `TradingDate` derives **only from a calendar** (AD-8). So the prop firm's day boundary must come from a calendar — but it is **not a market-hours calendar**; it is an accounting/evaluation boundary with no bearing on when the market is open. AD-8's naming ruling explicitly recognises only two calendar kinds: *"'Market-hours calendar' and 'news calendar' are distinct named concepts."* There is no third kind, and the prop-firm boundary is neither.
4. Therefore the prop-firm daily-loss boundary is either (i) expressed as a market-hours calendar, which is a category error that will corrupt session windows and bar boundaries for that venue, or (ii) computed outside the time model — meaning **the value that gates the operator's largest money risk is derived by machinery the framework does not govern**.
5. And because `TradingDate` carries no calendar identity (A-4), a prop-firm trading date and a market trading date **compare equal** when they name different spans.

Compounding clause:
> AD-8 bullet 1: *"**Local time is display-only** and always labelled."*
> DevOps audit (recorded as binding): *"DST invisible **BECAUSE no local time is ever stored/keyed/compared**."*

Evaluating a daily-loss cap against a boundary in the prop firm's stated timezone **is** a comparison in local time, and it gates real money. It is not display.

**Fix (new AD recommended, not an amendment):** introduce a third, explicitly-named calendar kind — an **accounting-boundary calendar** (or "day-boundary rule") — parameterized by **account**, not venue, supplying only a rollover rule and its zone, producing a `TradingDate` that carries its own calendar identity. Then state that market-hours calendars answer "is it open / which session", accounting calendars answer "which day does this belong to for evaluation", and that the two must never be substituted for each other. This costs one paragraph now and is unbuildable later without re-labelling stored evidence.

**Note (scope):** this does **not** model any prop firm — the operator's ruling that prop-firm Books are deferred to the agentic era stands. It only asks whether the ratified primitive can *hold* a per-account boundary. As written, it cannot.

---

### 3(c) — cTrader API facts vs the ratified time and identity rules

**Consistent (verified, no action):**
- UTC milliseconds → int64 ns storage is pure headroom, and AD-8's *"each source's actual resolution is stored beside the ns value"* correctly prevents consumers inferring sub-ms ordering. ✓
- No server-clock primitive → AD-8's receive-time recording rule is **mandatory, not optional**, and the spine states it. ✓ (Modulo C-1, which deletes half of it.)
- ms-resolution sources make same-instant ties routine → the `(instant, writer, sequence)` rule is well-founded. ✓
- `ProtoOATrendbar.utcTimestampInMinutes` (minutes) is representable and its resolution is storable. ✓

**Finding (F-15, HIGH) — a ratified AD asserts "verified" against research that says the opposite.**
> AD-8 bullet 6: *"Forex calendar ships first: 17:00 America/New_York rollover (**verified = cTrader's own boundary**)."*
> `ctrader-time-research.md` §2: *"**UNVERIFIED**: rule not stated in Open-API-specific primary docs, only platform-general threads."*
> AD-8 bullet 7, same AD: *"**No cTrader timestamp is trusted as UTC until venue verification (GAP-0037).**"*
> Memlog (GAP-0012 event): *"Findings presented **not auto-adopted** — **venue sitting ratifies**."*
> L3 (constitution): *"Research and study deliverables **remain evidence** until an operator ruling adopts them as QMF contracts."*

Five clauses, one word. The 17:00-NY boundary is almost certainly correct — the research grades it well-supported — but the spine records it as **verified** when its own cited source grades it unverified, in an AD that simultaneously says trust nothing from cTrader until GAP-0037. Either the operator has ratified it (in which case say so — "operator-adopted 2026-08-19, venue verification pending GAP-0037") or the parenthetical must read "consistent with cTrader's stated platform boundary (unverified in Open-API primary docs; GAP-0037)". A ratified spine must not launder a research grade.

**Finding (F-16, HIGH) — cTrader has two time authorities; a calendar has one rollover.**
> AD-8 bullet 6: *"every calendar supplies **a rollover rule** (24/7 included)"* (singular).
> Research §2: *"Daily bar boundary pinned to 17:00 America/New_York… **Symbols carry their own `scheduleTimeZone` for trading intervals**."*
> DevOps audit (binding): *"A session calendar may never be a fixed UTC offset from 'broker server time' (**cTrader-class servers run EET/EEST**)."*

Resolution in A-11: split rollover from schedule.

**Finding (F-15b, note-to-finding) — the 23h/25h trading day is acknowledged and unhandled.**
> Research §5: *"the 17:00-NY day boundary means daily bars are **23h/25h once a year each**."*
> AD-8 bullet 3: *"**Interval** (half-open, contains/overlaps), **SessionWindow**."*

Half-open intervals handle this correctly *if* every consumer treats session length as data rather than a constant. Nothing in the spine forbids a unit from assuming a 24h `SessionWindow`. One sentence — *"session and trading-day length is data; no consumer may assume a constant"* — closes it, and it costs nothing.

**Finding (F-17, HIGH) — the pinned tzdata may not be the tzdata used.** See A-12. This is the cTrader-adjacent finding that bites hardest, because the 17:00-NY rollover's UTC hour is derived from `America/New_York` DST rules, so a tzdb mismatch across AD-1's two tier-1 platforms moves the day boundary by an hour on the affected dates.

---

### 3(d) — Money scaled-integers vs cTrader's fixed-point encoding

**Finding (F-06, HIGH) — the `precision` tag has no stated referent, and cTrader has at least three scales.**
> AD-7: *"Money/Price/Quantity are whole-number counts of the smallest unit, **tagged with currency and precision**"*.
> cTrader encoding (operator-supplied): prices are fixed-point at **1/100000 units** — independent of the symbol's own declared `digits` (5 for EURUSD, **3** for JPY pairs). Volumes are carried at a separate scale; monetary values use a broker-configurable `moneyDigits`.

Three distinct scales, one `precision` field, no rule. Full attack in A-6. The concrete, testable consequence: **a USDJPY price crossing a package seam is silently off by a factor of 100** and both sides are AD-7-compliant.

**Finding (F-06b, HIGH) — no rule for arithmetic across differing precisions of one currency.**
`moneyDigits` is a **venue** property; AD-7 ties precision to **currency**. Summing USD balances across brokers with different `moneyDigits` has no defined behaviour: promote, round (which mode?), or refuse. AD-7 says *"rounding only at named venue/accounting boundaries with an explicit, stated mode"* — and **the spine names no such boundary and states no mode**. Portfolio equity across ~6 brokers is a day-one operator need.

**Finding (F-08, HIGH) — foreign money has no evidence discipline while foreign time has a full one.**
> AD-8 bullet 7: *"**Foreign timestamps are evidence**: stored verbatim with declared zone/offset/resolution… conversions are **derived values with lineage**; corrections are annotations, never rewrites."*
> AD-7: (nothing equivalent).

The asymmetry is the finding. A broker's raw price/volume/money integers plus their declared scale are exactly as much "foreign evidence" as its timestamps, and reconciling a disputed fill requires reproducing the venue's own arithmetic from the venue's own integers. The spine currently permits a unit to store only the converted value.

**Meta-finding (worth the operator's attention):** exact **time** was ratified with a two-lens audit **and** a dedicated venue research file. Exact **money** was ratified with neither, and the cTrader research file does not mention price/money encoding at all. AD-7 is the less-evidenced of the two exactness rulings, and it is the one that touches every order.

**Fix:** mirror AD-8 bullet 7 into AD-7: foreign monetary values are stored verbatim (raw integer + declared scale + declared digits + the venue's declared `moneyDigits`), conversions are derived with lineage, and the framework's own scale for each type is stated once and enforced at the venue boundary — which is then explicitly named as one of AD-7's "named venue boundaries", with its rounding mode stated.

---

### 3(e) — The result-label `world` field vs the parked sim-time machinery

**Direct answer: partially. `live` and `replay` are implementable today with no parked machinery. `simulated` is not.**

> AD-12: *"…and **world (live / replay / simulated)**… The world field **commits nothing about backtesting design**."*
> AD-8 bullet 1: *"**Every** stored timestamp is int64 UTC nanoseconds **since the Unix epoch**."*
> Memlog (GAP-0008 final): *"**Sim-time-as-type machinery PARKED** to backtesting sitting; minimal 'world label' (live/replay/simulated) moved into GAP-0012."*
> Deferred table: *"Backtesting… incl. **sim-time type machinery**… only the world label (AD-12) is fixed."*

- **`live`** — real clock, real instants. Implementable. ✓
- **`replay`** — AD-8 already provides the mechanism (*"replay injects a data-driven one"*), and the instants are genuine historical UTC observations. The label is a pure tag over real data. Implementable with zero parked machinery. ✓
- **`simulated`** — synthetic data (L20/DEC-0054) has **no real instant**. Yet AD-8 bullet 1 admits no exception, so a synthetic series must stamp int64 UTC ns "since the Unix epoch" for events that never occurred, making synthetic timestamps **type-identical to real observations**. The only thing separating them is the label — which is precisely the failure mode the parked `SimNanos` vs `UtcNanos` split was designed to prevent (`time-audit-devops.md`: *"Simulated/replayed time is a **DIFFERENT TYPE** (SimNanos vs UtcNanos), **not a flag**"*). AD-12 has adopted the flag and parked the type. ✗

**Second contradiction in the same area (F-10b): AD-12's Prevents exceeds its Rule.**
> AD-12 Prevents: *"…or **worlds mixing in merged ledgers**."*
> AD-12 Rule: *"…together these are its **identity**."*

Identity distinctness prevents **collision**, not **mixing**. Two results in different worlds get different fingerprints and can sit in the same table, same stream, same file. The DevOps rule that actually delivers the stated Prevents — *"replay may never write into the live evidence namespace"* — is a **storage/namespace** rule that the spine did not carry over.

**Third (F-09 restated from the label's side):** with account roles including two paper flavours and `world` including `live`, the mapping is undefined, so the label is not yet a well-defined function of the run. See A-7.

**Fix (three sentences, all cheap now):**
1. State that `live` and `replay` both use real UTC instants and that a replay clock is a pure function of the data cursor (already implied by AD-8 — just say it).
2. Either drop `simulated` from V1's enum (AD-11 already permits adding enum members later, and AD-12 says parts are addable) **or** state now that a simulated world's instants are a distinct time domain that may never be stored in the same field as observed instants. Do not ship an enum member whose type story is parked.
3. Add the namespace rule: a non-`live` world may never write into the live evidence namespace — the identity rule does not deliver the Prevents on its own.

---

## 4. Notes — attacks I declined as later-sitting territory

Recorded so the operator can see the sweep was bounded deliberately, not by omission.

- **Observation dedup policy, store layout, retention, split boundaries** — data sitting (GAP-0020..0030). *But* the **absence of any defined primary key** once AD-8 bans timestamps as keys is a foundation hole and appears as F-14.
- **Order state machine, secrets, adapter contract, rate-limit/chunking discipline** — venue sitting (GAP-0035..0038). The cTrader research's 50/s + 5/s + 1-week-span facts are ingest-design inputs, not spine contradictions.
- **Trendbar BID-basis** — venue sitting resolves it; the research grades it staff-authoritative-but-undocumented. Consistent with the spine. The only spine-adjacent consequence is that bar identity must record its price basis, which is a `qmf-data` contract detail.
- **Bot↔Book cardinality (DEC-0040) and exit ownership (DEC-0067)** — both are live conflicts in the gap report, both are risk/registry territory, neither touches AD-1..AD-14.
- **Registration/promotion evidence, attempt counters, lineage edge types** — registry sitting (GAP-0014..0019).
- **Inter-library dependency edges beyond core** — explicitly Deferred by the spine, correctly.
- **Swap-Wednesday drop** — consistent with swap-free accounts. One small carry-forward: `tracker/map.md` records that *"the swap-free account means the `financing` P&L column models an **admin fee**, not swap"* — so a scheduled financing charge may still exist even without swap. Dropping settlement machinery from V1 is fine; just don't let a later unit conclude "no swap ⇒ no dated financing at all."
- **Numeric performance budgets** — correctly deferred to first measurements; the *method* problems with AD-13 are in C-8.

---

## 5. What I would change before this spine ships

Ordered by cost-of-fixing-later, highest first. All five CRITICALs are cheap now and expensive after evidence is written.

1. **Reconcile monotonic persistence** (C-1) — one sentence. After the first month of stored ticks, changing the record shape means a format-version mint and a migration of everything.
2. **Split log timestamps from journal timestamps** (C-2) — one sentence. After the fact, ISO-8601 journal rows have already lost ns and sequence; the data is not recoverable.
3. **Give `TradingDate` its calendar identity, and mint an account-scoped accounting-boundary calendar** (F-04) — one paragraph. After the fact, every stored trading date is ambiguous and cannot be disambiguated retroactively.
4. **Name which version ladder the result label carries** (C-5) — one clause. After the fact, every existing label is in the wrong ladder.
5. **Define "the money path" as a taint rule and settle float-in-fingerprint** (C-4) — one paragraph. After the fact, artifacts are irreproducible across the two tier-1 OSes and nobody knows which ones.

Then the HIGH tier, of which the four I would not ship without are: **F-06** (which precision?), **F-11/F-12** (the fingerprint recipe and the idempotent-merge carve-out), **F-14** (writer identity + what the primary key actually is), and **F-17** (force TZPATH to the pinned tzdata).

**One structural observation to close.** Every CRITICAL above has the same shape: an AD states a rule *absolutely* and a sibling clause states an exception *equally absolutely*, with no reconciliation sentence. That is a symptom of ratifying gap-by-gap without a closing pass — which is exactly why the operator ordered this sweep, and it worked. The spine's individual rulings are sound. It is the seams between them that a factory unit will fall through.
