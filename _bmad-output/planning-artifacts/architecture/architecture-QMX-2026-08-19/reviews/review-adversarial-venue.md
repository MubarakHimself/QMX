# Adversarial Review — the venue increment (AD-26, AD-27, AD-28 + the AD-8/AD-9 amendments)

- **Target:** `ARCHITECTURE-SPINE.md` (status: final, updated 2026-08-20)
- **Scope:** AD-26 (venue secret lifecycle), AD-27 (venue commands + uncertainty
  law), AD-28 (adapter contract + capability discovery), and the 2026-08-20
  amendments to AD-8 (cTrader venue facts, measured daily boundary) and AD-9
  (broker-identity-is-deployment) — in interaction with AD-1 … AD-25.
- **Companions consulted:** `ctrader-venue-facts.md` (bundles A/B/C),
  `trading-node-order-path-study.md` (the CT-ADAPTER-01 caller, the seven doors,
  the CM's ratified ownership set).
- **Prior passes:** `review-adversarial.md`, `-2`, `-3`. All three ran before
  AD-26/27/28 existed. Review 3 covered AD-22…AD-25 and explicitly parked venue
  as later-sitting territory. **This increment has never been adversarially
  reviewed.** A high critical count here is a signal of youth, not of quality.
- **Date:** 2026-08-20

---

## 1. Method

I am not hunting for omissions. I am building **pairs of units one level down** —
the concrete adapters, sinks, and roots a factory agent would write from these
ADs — where *both* units obey every ratified clause to the letter and the two
still cannot be assembled. The canonical pair for this increment is:

- **Unit A — the cTrader adapter** (`qmf-venue` adapter #1, the one being built
  now, against the ratified `ctrader-venue-facts.md` surface).
- **Unit B — a future CCXT-class crypto adapter** (the one AD-28 promises "slots
  in later by declaring a different record through the same port").

Secondary pairs: **adapter vs composition root** (who mints, who persists, who
blocks) and **adapter vs consumer** (who reads capability, who resolves UNKNOWN).

Severity rule, unchanged from review 3: divergence that fails loudly at tier 2 is
rated lower; divergence where both units run, both pass their own gates, and
write **different identities or different numbers into permanent, append-only
evidence** is critical. Fingerprints are forever; an identity fork is the one
class of defect this architecture cannot repair later.

**Verdict:** the venue rulings are sound and the uncertainty law is the right
law. The seams are not yet tight enough to hand to two adapter teams. Thirty
places will produce divergent-but-conformant implementations; nine of them
contaminate permanent evidence or the money path rather than merely failing to
compile. Three of the nine are cases where AD-27/AD-28 **do not inherit a cure an
earlier AD already paid for** (AD-25's read-time fold, AD-10's collision split,
AD-7's named-boundary discipline).

**Counts: 9 critical, 15 high, 6 medium (30 total).**

---

## 2. Critical — two conformant units WILL diverge in permanent evidence or on the money path

### C-01 — Command identity mapping is not required to be injective, total, or reversible

- **Unit A (cTrader):** AD-27 says the command identity is "derived from its `fp1`
  fingerprint, mapped into the venue's client-id field (mapping and any length
  bound declared in the CT-18 record)." `clientMsgId`/`label` tolerate the whole
  75-character `fp1:sha256:<64 hex>` string, so A declares the mapping as the
  identity function and the length bound as 100. Reverse mapping is free.
- **Unit B (crypto):** the venue's `clientOrderId` is 36 characters (Binance) or a
  UUID (Coinbase). B declares in CT-18 a truncation mapping — the first 32 hex
  characters of the digest — plus the length bound. Also verbatim conformant:
  AD-27 requires only that the mapping *be declared*.

**Divergence.** Three consequences, all silent:

1. **The idempotency law inverts.** AD-27: "Re-presenting the same command is an
   idempotent accept … differing content under a reused identity is refused and
   alarmed." B can only see the *venue-side* id. Two economically distinct
   commands whose digests share a 128-bit prefix — or, if a future adapter
   declares a 16-hex-character mapping to fit a shorter field, a far smaller
   space — arrive at the venue under one id. B's venue accepts the second as an
   idempotent re-present of the first, or rejects it as a duplicate. Either way
   an order is lost or doubled, and nothing alarms, because the collision test
   AD-27 describes was never performed against the *full* fingerprint.
2. **Reconciliation loses its correlation key across a restart.** CT-20's
   read-back returns venue-side client ids. A's read-back is a total function
   back to command fingerprints. B's requires a durable (venue-client-id →
   command fingerprint) side table, and **nothing in AD-27 or AD-28 requires that
   table to be persisted, let alone to be a registry record kind**. B's adapter,
   restarted mid-uncertainty, cannot correlate anything and returns `unknown`
   forever — which, per C-02 and H-08, blocks the command pipe permanently.
3. **`close_all` breaks the mapping outright** (see C-08): one `fp1`, N venue
   submissions, N client ids. Neither A nor B has a declared rule.

**Severity: critical** — duplicate or lost orders on the live money path, with no
detection.

**Minimal clause (AD-27, command identity):**
> The command identity mapping declared in CT-18 MUST be injective and total over
> the `fp1` digest space. Where the venue's client-id field cannot carry an
> injective encoding of the full digest, the adapter MUST persist a durable
> `command-id-binding` registry record — (venue-client-id, command `fp1`,
> account, session epoch) — through the composition root's sink **before**
> submission, and that binding is a named part of CT-20's reconciliation
> evidence. The idempotency and collision tests of AD-10 are performed against
> the full locally-held fingerprint, never against the venue-side id. A mapping
> that is lossy without a persisted binding is a contract defect.

---

### C-02 — "Stream" is named three different ways; the UNKNOWN block, the WriterId, and the gapless sequence can legally split

The spine uses three distinct granularity words for one concept:

- AD-27: "While an `UNKNOWN` is outstanding on an **account-binding stream**, the
  adapter refuses new commands on that stream."
- AD-28: the CM "holds the `WriterId` for every **venue-session stream**."
- AD-15/AD-8: one writer per stream; `WriterId` minted per (machine, role,
  **stream**).

And AD-28 contemplates all three cardinalities at once: "connections required for
simultaneous environments, **accounts per connection**", plus paired-demo
bindings and "shared-account order-lifecycle merges".

- **Unit A (cTrader):** stream = account-binding, verbatim from AD-27. Two Books
  bound to one live account are two streams. An outstanding UNKNOWN on Book 1
  does not block Book 2.
- **Unit B (crypto):** stream = venue session, verbatim from AD-28. One
  connection carries three accounts; an UNKNOWN on any one blocks all three.
- **Unit C (a third reading, equally textual):** stream = (venue, account),
  because that is the unit whose *venue-side order state* is actually shared.

**Divergence.** This is not an availability difference, it is a safety
difference. Under A, while a `place_order` on account X is UNKNOWN, Book 2 may
legally submit `close_all` on the same account X — flattening a position whose
existence is unknown, or placing a second order into an uncertainty window the
law exists to freeze. Under B, one account's uncertainty freezes two unrelated
accounts including their protection commands. The after-condition
("reconciliation") also resolves at a different granularity in each: A
reconciles a binding, B a session, and neither matches the venue's actual unit of
order state.

Worse, because the *same word* names the WriterId unit and the sequence unit, A
and B produce a different **number of journal streams** for the same deployment
(AD-21: "the journal is N streams — one per producing component … gapless
per-(writer, boot-epoch) sequences (a gap signals loss)"). Two adapters, two
stream topologies, two incompatible gap-detection semantics over the same
evidence store.

**Severity: critical** — a protection command permitted inside an uncertainty
window, plus a fork in journal-stream topology.

**Minimal clause (AD-27 + AD-28 + AD-15, one definition):**
> **Command stream** is defined exactly once, for all three purposes: the unit of
> UNKNOWN blocking, of `WriterId` ownership, and of the gapless per-writer
> sequence is the **(VenueId, account) pair** — the narrowest unit that shares
> venue-side order state. It is deliberately coarser than the account-binding
> (all bindings on an account block together, protection commands included, per
> H-12's priority carve-out) and strictly finer than the connection (a shared
> connection never couples the uncertainty state of distinct accounts). The words
> "account-binding stream" and "venue-session stream" are struck; sessions and
> bindings remain, but neither is a stream.

---

### C-03 — The order-state machine is written as a gate on an immutable store; AD-25 already paid for the cure and AD-27 does not inherit it

AD-27 declares a machine: `client-submitted → venue-accepted | venue-rejected |
UNKNOWN; venue-accepted → partially-filled* → filled | cancelled | expired |
closed-by-venue`. Three real venue behaviors have no legal edge in it:

- a **fill arriving for a command never observed as accepted** (routine on
  cTrader when the accept is lost across a disconnect, and normal on venues that
  emit execution before acknowledgement);
- a **cancel racing a fill** (C-09);
- a **venue that acks cancels implicitly** (C-09).

- **Unit A:** an inbound event whose transition is not in the declared machine is
  an AD-11 `invalid input` refusal. The event is not recorded and no `fill`
  journal event is emitted (AD-27 ties emission to observation). The position
  drifts from evidence; reconciliation returns `drift`; the node takes a
  technical kill. A cites AD-27's machine and AD-11's refuse-don't-guess rule.
- **Unit B:** synthesizes a derived `inferred-accepted` observation so the machine
  advances, then records the fill. B cites AD-27's "first-class, append-only
  observations", AD-28's "foreign values verbatim … conversions are derived with
  lineage", and AD-19's correction-by-annotation idiom.

**Divergence.** A's evidence stream has holes where fills happened; B's has
synthetic venue events that no venue ever sent. The two streams are not
reconcilable against each other, their journal event counts differ, and their
per-writer sequences differ. Both pass their own contract tests.

This is precisely the failure AD-25 lists among its **Prevents** — "a mutable
state machine sitting on the immutable store" — and AD-25 cured it: "Current
state … is a **read-time fold** over the object's edge stream." AD-27 reintroduces
the shape without the cure.

**Severity: critical** — permanent evidence diverges, and one of the two branches
silently loses fills.

**Minimal clause (AD-27, order-state observations):**
> Recording is unconditional and precedes interpretation. Every inbound venue
> event is stored verbatim with its receive stamps and journaled **before** any
> state evaluation; the order-state machine is a **read-time fold** over the
> observation stream per CT-20's stated read-resolution rule (mirroring AD-25),
> never a gate on recording. An observation whose transition is not legal under
> the declared machine is recorded, annotated with a typed `out-of-sequence`
> edge, and forces the owning command's outcome to `UNKNOWN` pending
> reconciliation. **Adapters never synthesize venue observations**; a derived
> state is a fold result, never a stored event.

---

### C-04 — The error-mapping table has no pinned row shape, and its unmapped default is fail-open on both retryability and outcome class

AD-28: "Every venue error code maps to the AD-11 taxonomy through a versioned
per-adapter table; unmapped codes become `transient venue failure` plus an
alarm — never an invented category."

- **Unit A (cTrader):** the table is `code → category`. Retryability is derived
  from category by a rule A invents, because AD-11 defines retryability as a
  refusal field but never defines a category→retryability function.
- **Unit B (crypto):** the table is `(code, command context) → (category,
  retryability, after-condition)`, because the same code means different things
  on place vs cancel. Also verbatim conformant.

**Divergence, three ways, each on the money path:**

1. **Retryability forks.** Under A, everything mapped `transient venue failure` is
   retryable, so cTrader's error 35 (INCORRECT_BOUNDARIES — a permanent,
   caller-side fault) presents as retryable. AD-27 says "retryability rides typed
   refusals"; the node obeys the field, and retries a request that can never
   succeed.
2. **The unmapped default is the worst possible default.** An unmapped
   *permanent* error (unsupported order type, unknown symbol, account
   restriction) becomes `transient venue failure` = retry forever under A.
3. **Outcome class is undefined for venue-returned errors.** AD-27: "A transport
   error, timeout, or disconnect yields `UNKNOWN`." A venue-returned error code
   is none of those — but it maps to the same `transient venue failure` category
   the stream-block uses. Unit A therefore treats any `transient venue failure`
   out of `submit()` as `rejected-by-venue` (it came from the venue); Unit B
   treats it as `UNKNOWN` (fail-safe). **A duplicates orders; B blocks the pipe.**
   Both cite AD-27.

**Severity: critical** — the same venue response produces "order rejected" on one
adapter and "order state unknown" on the other.

**Minimal clause (AD-28, error mapping):**
> The mapping table's row shape is pinned contract surface:
> `(venue-code, command-or-event-context) → (AD-11 category, retryability,
> after-condition, submission-outcome class)` where submission-outcome class ∈
> `{rejected-by-venue, UNKNOWN}`. A venue-returned code may be read as
> `rejected-by-venue` **only** where the table declares it so; every other path
> resolves `UNKNOWN`. The unmapped default is
> `(transient venue failure, retryable = no, outcome = UNKNOWN)` plus the alarm —
> never retryable-by-default. Category alone never implies retryability.

---

### C-05 — Who holds the WriterId and who performs the write are separable, and one legal wiring is fail-open on unpersistable evidence

AD-28: the CM "holds the `WriterId` for every venue-session stream (AD-15)."
AD-25 (the house pattern for edge modules): records are "minted by the
composition root, which holds the WriterId and the gapless per-(writer, kind)
sequence; **the library returns fingerprintable content, never stamped records**."
AD-15: "a 'writer' here IS the holder of an AD-8 `WriterId`."
Default-deny: nothing imports `qmf-venue`, and `qmf-venue` imports only
`qmf-core` — so the adapter cannot import `qmf-data` (journal) or `qmf-registry`
(records).

- **Unit A (adapter team):** the root injects core-defined sink protocols
  (`ObservationSink`, `JournalSink`); the CM stamps writer + sequence and calls
  them. Cites AD-28 + AD-15. No dependency edge is created (AD-22 precedent:
  "Declaring an input creates no package dependency edge").
- **Unit B (root team):** the adapter returns fingerprintable content; the root
  stamps and persists. Cites AD-25's explicit pattern and AD-2's "records/
  lifecycle **owned** by `qmf-registry`".

**Divergence.** AD-27 requires that "an unpersistable journal event is a typed
refusal that **blocks new commands**." Under A the CM learns of the sink failure
synchronously and blocks. **Under B the adapter never learns** — the failure
happens in the root, after the adapter returned. Nothing in CT-19 gives the root
a way to tell the adapter to block; no such method is declared anywhere. B's
adapter keeps accepting commands after its evidence stopped persisting. That is a
fail-open on the money path, produced by faithfully following AD-25's pattern.

Secondary: under B the process that actually writes the stream is not the
`WriterId` holder, violating AD-15 in the letter.

**Severity: critical** — one legal wiring trades on an account whose evidence is
not being written.

**Minimal clause (AD-28, sinks and writers):**
> The venue path uses the **injected-sink** wiring, and AD-25's root-mints
> pattern does not extend to it. The composition root injects core-defined sink
> protocols (`ObservationSink`, `JournalSink`, `SecretStore`, `RecordSink`);
> the CM holds the `WriterId`, stamps writer + sequence, and calls them
> synchronously. Every sink returns success or an AD-11 refusal to its caller;
> a `storage failure` from any sink is the trigger for the command-pipe block of
> AD-27 and blocks it **in the component that holds the WriterId**. Rationale is
> stated in-band: the block-on-unpersistable rule requires the writer to see the
> failure.

---

### C-06 — Secret reference names are identity-bearing by AD-10 default; that both leaks deployment identity into permanent evidence and breaks fingerprint-equality

AD-26: components handle "**secret references** (typed names)"; a refusal carries
"the reference name, never the value"; secrets never appear in fingerprints.
AD-28: "paired-demo bindings are **secret-reference-only records**."
AD-10: "every contract field is identity by default; display-only exclusion
requires an explicit, versioned declaration."

So the reference **name** is, by default, an identity field of the binding record
and enters `fp1` and every artifact citing that binding. AD-26 forbids values in
fingerprints; it says nothing about names.

- **Unit A:** mints opaque reference names (`ref/7f3a91`).
- **Unit B:** mints descriptive names, which every real deployment does:
  `ctid-12345678-<brokername>-live-9876543-clientsecret`. Verbatim conformant —
  AD-26 constrains the value, not the name.

**Divergence, two attacks:**

1. **Deployment identity is written permanently into evidence.** B's fingerprints
   now contain broker name and account number, in an append-only store that
   "never loses the ability to read its own history" (AD-5). This directly
   defeats the AD-9 amendment — "broker identity is deployment configuration,
   never architecture … no rule anywhere may name a specific broker" — by the
   evidence door rather than the rule door. The same name rides the AD-11 refusal
   context, which AD-14 propagates into structured logs "exportable to standard
   monitoring stacks" — i.e. off the machine.
2. **The sharper one: fingerprint equality stops implying identity.** A reference
   name resolves against the *deployment environment's* store. Two environments
   using the same reference name with different underlying credentials produce
   binding records with **identical bytes and identical fingerprints attesting
   different accounts**. AD-10's collision rule splits on "same hash, byte-
   identical content → accepted silently (the sandbox-merge normal case)" versus
   "same hash, differing bytes → refused and alarmed". This case is the first
   branch: **silently accepted, undetectable, wrong**. A demo binding and a live
   binding can dedupe into each other.

**Severity: critical** — an undetectable identity collision on the account
binding, plus permanent leakage of deployment identity.

**Minimal clause (AD-26 + CT-21):**
> (a) A secret reference is an **opaque minted id** under AD-9's discipline —
> operator-minted, stable, never reused, and never encoding venue, broker,
> account, environment, or key material; any human-readable label is a separate
> field held outside evidence. Construction validates this (`invalid input`).
> (b) An account-binding record's identity is **(VenueId, AccountId, role,
> world)**; the secret reference is declared occurrence/display-only and excluded
> from `fp1` — a credential is a deployment fact, not a market fact (the AD-9
> amendment applied to evidence). (c) Refusals, logs, health reports, and metrics
> carry the reference **id** only.

---

### C-07 — cTrader's execution prices are binary doubles; AD-7's foreign-money clause covers only integers, so the fill price can legally sit outside identity

AD-7: "a venue's **raw integers** are stored verbatim with their declared scales
(e.g. cTrader's 1/100000 wire price scale, per-symbol `digits`, per-account
`moneyDigits`)."
`ctrader-venue-facts.md` A6: "**execution prices are raw doubles** (position
price, SL/TP, deal `executionPrice`, conversion rates) — uniform /100000 would
corrupt the execution path."
AD-10: "floats are refused in identity content."

The single most money-path-critical value the adapter handles — the price a fill
happened at — is a binary double, and the verbatim-storage clause does not cover
it.

- **Unit A:** stores the double verbatim in the observation record, declared
  display-only so AD-10's float ban is satisfied. "Verbatim" honored.
- **Unit B:** refuses to admit a float; crosses AD-7's named adapter boundary
  immediately to a scaled integer at the symbol's `digits` with a declared
  rounding mode, keeps the raw double as an integrity-checked provenance blob
  (AD-10's float-artifact idiom).

**Divergence.**

1. Different identity content for the same fill → different fingerprints → no
   dedup, no cross-adapter reconciliation.
2. **A is unsafe on its own terms.** With the price display-only, two different
   fills on the same order — same quantity, same instant bucket, different price
   — produce **byte-identical records** and therefore an AD-10 "idempotent
   re-write, accepted silently". One fill swallows the other, permanently, with
   no alarm.
3. Even between two Unit-B-style adapters, the target scale is unpinned: `digits`
   vs the 1/100000 market-data scale are both "a declared scale" under AD-7, and
   produce different integers, different fingerprints, and different P&L for the
   same economic fill.

**Severity: critical** — silent fill loss on one branch, identity fork on the
other, both on the money path.

**Minimal clause (AD-7 amendment + CT-18/CT-20):**
> Foreign money arriving as a **binary float** is never storable as an identity
> field. It crosses AD-7's named adapter boundary at the point of receipt to a
> scaled integer whose target scale is pinned **per value class in CT-18**
> (execution price → the symbol's `digits`; money → the account's `moneyDigits`,
> absent `moneyDigits` being a refusal per venue-fact C4; market data → the
> declared wire scale) with the rounding mode declared and identity-bearing. The
> raw float is retained only as integrity-checked provenance and is never the
> value any consumer reads. **Fill price, fill quantity, the venue instant, and
> the receive instant are mandatory identity fields of a fill observation** and
> may never be occurrence-classified.

---

### C-08 — `close_all` has no declared scope and no compound-command law; on a shared account it can legally liquidate another Book

AD-27 fixes the vocabulary at four kinds including `close_all`, and states that
AD-27 "binds only the mechanical surface". AD-28 explicitly contemplates shared
accounts ("shared-account order-lifecycle merges use only the caller's sequencer
evidence") and paired-demo bindings.

- **Unit A (cTrader):** the venue has no native close-all; A implements it as a
  loop over every open position on the account. Scope = account.
- **Unit B:** scope = the caller's account-binding; positions belonging to other
  bindings on the same account are untouched.

**Divergence.** On a shared account, A's `close_all` — issued by Book 1's kill
path — liquidates Book 2's positions. Both readings are textual; AD-27 names the
kind and never names its scope.

Compounding: `close_all` is **one** command identity fanning out to N venue
submissions, which breaks C-01's mapping outright, and the three-outcome law has
no meet operator. A returns `accepted-by-venue` if any child succeeded; B returns
`UNKNOWN` unless all did. A flatten that half-worked is reported as success.

**Severity: critical** — unauthorized liquidation of another Book's positions,
and a half-executed flatten reported as complete.

**Minimal clause (AD-27, command vocabulary):**
> `close_position` and `close_all` carry a **required typed scope** field —
> `account | account-binding | instrument-within-binding` — and CT-18 declares
> which scopes the venue supports natively; an unsupported scope is an
> `unsupported capability` refusal, never emulated at a wider scope. A command
> that fans out to N venue submissions is a **compound command**: each child
> carries a derived identity (`fp1` of the parent plus its declared ordinal),
> each child is individually observation- and journal-bearing, and the parent's
> outcome is the meet of its children — any child `UNKNOWN` makes the parent
> `UNKNOWN`, any child `rejected-by-venue` makes the parent
> `partially-executed`, which is a named outcome, not a success.

---

### C-09 — Cancel acknowledgement mode is undeclared; implicit-ack venues and cancel/fill races write mutually contradictory permanent evidence

- **Unit A (cTrader):** cancels are acked by an explicit execution event
  (`ORDER_CANCELLED`). The cancel command resolves `accepted-by-venue` on the
  event; the order observation folds to `cancelled`.
- **Unit B (a venue that acks cancels implicitly** — HTTP 200 with no event, the
  order simply absent from the next open-orders read): B must derive the outcome
  from a read-back. B declares "resolution by absence in read-back" in CT-18.

**Divergence.**

1. **The three-outcome law makes B unusable or unsafe.** Every cancel is
   `UNKNOWN` until reconciliation, so the stream blocks on every cancel (AD-27)
   — or B declares absence sufficient for `accepted-by-venue`, at which point the
   two adapters mean different things by the same outcome word: A's means "the
   venue said yes", B's means "the venue did not say no and the order was later
   absent".
2. **The race writes contradictory evidence.** Cancel submitted; fill lands
   first. Under A the cancel is `rejected-by-venue` via the error table
   (ORDER_NOT_FOUND class) and the order folds to `filled`. Under B the read-back
   shows no open order → cancel `accepted-by-venue` → the journal records the
   order as **cancelled while a fill for the same order also exists**. Both rows
   are in an append-only store forever; the read-time fold has no rule for
   preferring one.
3. Nothing in AD-27 separates **command outcome** from **order state**, so a
   builder is invited to merge them.

**Severity: critical** — contradictory terminal states in permanent evidence, and
a position believed closed that is open.

**Minimal clause (AD-27 + CT-18/CT-20):**
> CT-18 declares, per command kind, the venue's **acknowledgement mode**
> (`explicit-event | implicit-absence | none`). An outcome is never derived from
> absence alone: a cancel resolved by read-back resolves `accepted-by-venue` only
> if the read-back also shows no fill for that order with a venue instant at or
> after the cancel's submit stamp; where such a fill exists the cancel resolves
> `rejected-by-venue (superseded-by-fill)`. **Command outcome and order state are
> separate streams and are never merged**: an order's terminal state is decided
> by fills and venue lifecycle events only, never by a cancel command's outcome.

---

## 3. High — two conformant units diverge in shape, wiring, or measurement

### H-01 — No normative (command × outcome) → journal-event-type mapping; the journal taxonomy forks per adapter

AD-21 fixes seven event types (decision, order, fill, risk transition, promotion,
data quality, control action). AD-27 says only "every observation emits AD-21
`order`/`fill` journal events." Unresolved for two builders: is a `cancel_order`
an `order` event or a `control action`? Is `close_all` an `order` event or a
`control action` (the node treats it as a KSA effect)? Does `denied-locally`
produce a `decision` event, an `order` event, or nothing? Is there one journal
event per observation, or one per order-state transition (so A emits 5 for an
order's life and B emits 2)? All four splits are legal, all four change the
permanent evidence a consumer filters on.
**Severity: high.**
**Clause:** CT-20 ships an **exhaustive, versioned mapping table** — (command
kind × outcome) → event type, and (observation kind) → event type — as contract
surface, not adapter judgment; plus the cardinality law: exactly one journal
event per recorded observation, exactly one per command submission, exactly one
per command outcome.

### H-02 — `denied-locally`: outcome or typed refusal? Two legal CT-19 signatures, and one produces no evidence of the denial

AD-27's "three-outcome law" enumerates four values, `denied-locally` among them.
**Unit A** returns it as an AD-11 typed refusal (`policy rejection`) — textbook
AD-11, and no observation record is created because nothing was submitted.
**Unit B** returns it as an outcome value in CT-19's success type, minting an
observation and a journal event. The two CT-19 signatures are different types, so
the node compiles against one; and A leaves **no evidence that a command was
denied**, which the node's own L11 rule ("a no that is not journaled is a
violation") forbids — but L11 is node law, not QMF law, so a QMF-only builder has
no reason to reach for B.
**Severity: high.**
**Clause:** pin it — `denied-locally` is an **outcome**, never a refusal. CT-19
returns an `Outcome` on every path where the command was well-formed and the
adapter reached a decision; typed refusals are reserved for malformed commands,
undeclared capability, and stream-blocked state. Every outcome, `denied-locally`
included, mints an observation record and a journal event. Rename the law
"four-outcome" or state that `denied-locally` sits outside the three venue
outcomes by construction.

### H-03 — The capability record mixes static declaration, broker-measured facts, and tunable constants; a rate-limit change mints on one adapter and not the other

AD-28's capability record contains order kinds and topology (static), span caps
and rate limits (per venue-facts C3/C7/C8, **empirically discovered**), the
measured daily boundary and verified spot-timestamp unit (AD-8 amendment:
"stored as broker-scoped configuration"), and "the adapter's declared
conservative window model" (a tuning knob). AD-10 makes every field identity by
default and AD-16 derives the record's stable id from its fingerprint.
**Unit A** publishes one static record per adapter version; a venue rate-limit
change means a new adapter release. **Unit B** publishes one per (adapter, venue,
account), minted at first connection, and mints a new record with a `supersedes`
edge whenever a measured limit changes. Both are "versioned, fingerprinted."
Consequence: whether a throttle tweak changes a fingerprint that downstream
artifacts cite is adapter-dependent — and the spine never says whether the
capability fingerprint is identity-bearing downstream at all, while AD-22 makes
the adapter's *instrument-metadata* snapshot fingerprints explicitly
identity-bearing.
**Severity: high.**
**Clause:** split CT-18 into two artifacts. (1) **Capability declaration** —
static, adapter-version-scoped, containing no measured or tunable value; its
fingerprint **is** identity-bearing for any artifact whose decode depended on it
(scales, quote side, bar provenance). (2) **Venue-observation profile** — per
(VenueId, account), append-only with `supersedes` edges, holding every
empirically measured fact; declared occurrence/provenance, **not** identity-
bearing downstream. Throttle and window tuning live in neither: they are node
configuration under the do-not-default standing.

### H-04 — "Consumed before use" versus "measured at first connection": the two are wired in opposite orders

AD-28 requires the capability record to be "consumed before use" and makes the
first-connection verification suite "a named part of the adapter contract", while
several capability facts (span caps via error 35, daily boundary, spot-timestamp
unit, BID-bar quote side) are only knowable after connecting with credentials.
**Unit A** publishes a static record at import; measured fields are simply absent
(AD-10: an absent value is an omitted key — legal), so a consumer may never
invoke them, and bars whose quote side was never reconciled get used anyway.
**Unit B** publishes nothing until the connection and suite complete; a pre-
connect capability query returns `unavailable dependency`. The two demand
opposite composition-root wiring orders — A wires everything at construction, B
must connect (network, secrets) before it can decide what to wire — so one root
cannot host both adapters.
**Severity: high.**
**Clause:** pin two phases. Phase 1 **declaration** is importable without
credentials and marks each field `static` or `measured-at-connection` with the
verification it requires. Phase 2 **verification profile** is produced post-
connect per (venue, account), carrying each measured value and a pass/fail
verdict journaled as `data quality`. A `measured` capability is `unavailable
dependency` (not `unsupported capability`) until its profile exists; consuming a
measured-but-unverified capability in evidence-bearing work is a `policy
rejection`. Wiring order is fixed: declaration at construction; profile before
the first command and before any evidence-bearing decode.

### H-05 — Demo credentials produce `world = live` evidence inside factory sandboxes, and AD-10 explicitly supports merging sandbox evidence

AD-26 permits factory sandboxes to hold demo credentials. AD-12 states that
because the account role carries money-reality, "paper/demo runs are `world =
live`". AD-12 also states that "factory sandboxes never produce timestamps that
enter an evidence store" and that a non-live world may never write into the live
namespace — but a demo run *is* the live world by AD-12's own definition, and
AD-10 designs for sandbox merges as the normal case.
**Unit A** (integration-test author) runs CT-19/CT-20 tier-2 contract tests
against a demo account and writes `world = live` observations. **Unit B** refuses
to write any evidence from a sandbox and tests against recorded fixtures under
`world = replay`. A's test orders are mergeable into the operator's live-namespace
registry, and AD-10's dedup will accept them silently.
**Severity: high.**
**Clause:** restate AD-12's namespace rule as role-scoped: the live evidence
namespace admits only records whose account-binding role is `live`; `demo`,
`paper-validation`, and `paper-benched` write to role-scoped namespaces within
`world = live`. Additionally, evidence produced in a factory sandbox carries an
identity-bearing `provenance = sandbox` field that blocks dedup-merge into the
operator store.

### H-06 — The receive-monotonic stamp is optional, so the six AD-13 latency rungs can legally be measured on the wall clock

AD-8 makes the boot-scoped receive-monotonic diagnostic "**optional**", while also
ruling that "a duration used for latency, timeout, cooldown, or cadence must be
measured monotonically; a duration derived from two wall instants is an evidence
span, never an elapsed-time measurement." AD-28 defines six latency rungs and
says "the adapter owns the arrival/submit stamps for its stages."
**Unit A** stamps wall time only and computes the rungs as wall differences —
conformant with AD-28 and with AD-8's optional clause, while producing exactly the
number AD-8's monotonic rule forbids (and, under AD-8's ops rules, containing the
live NTP slew). **Unit B** stamps both and computes monotonically.
AD-13 baselines are fingerprinted merge-gate artifacts, so the two adapters feed
the same rung with numbers measured by different instruments.
**Severity: high.**
**Clause:** AD-28 amends AD-8's optionality for the venue path — the boot-scoped
monotonic receive stamp is **mandatory** on every inbound venue event and on
every AD-13 rung boundary. A latency rung is defined as a monotonic delta within
one boot epoch on one machine; a rung computed from wall instants is refused as a
baseline.

### H-07 — WriterId granularity plus the missing session epoch: a reconnect is indistinguishable from evidence loss

AD-8 mints `WriterId` per (machine, role, stream) with a **boot/epoch id** so
"restarts are visible without changing writer identity", and AD-21 makes
sequences gapless per (writer, boot-epoch) where "a gap signals loss". cTrader
requires two connections for demo + live; sessions reconnect constantly, and a
session restart is **not** a boot.
**Unit A** mints one WriterId for the adapter role and interleaves both
connections into one sequence — which then collides with AD-28's rule that
shared-account merges use "only the caller's sequencer evidence", since the
adapter's own sequence already ordered them. **Unit B** mints one per session,
producing two journal streams where A produces one. Neither has a defined
behavior for the sequence across a reconnect: reset reads as loss, continue
requires durable sequence state nobody was told to persist.
**Severity: high.**
**Clause:** WriterId granularity on the venue path is **(machine, adapter role,
VenueId, account)** — the same unit as C-02's command stream. A **session-epoch
id**, distinct from the boot epoch, is carried on every venue observation so a
reconnect is visible; **sequences never reset on reconnect**, only on boot, and
the sequence cursor is durable through the same sink that persists observations.

### H-08 — Nobody is named as the party that clears an UNKNOWN block, and one reading livelocks on any open position

AD-27 sets the after-condition to "reconciliation" but assigns "when
reconciliation runs and what a verdict triggers" to node/BMS authority.
**Unit A**'s adapter exposes `reconcile()` and clears its own block when the
read-back accounts for the outstanding command — the adapter has acted on a
verdict, which AD-27 assigned elsewhere. **Unit B**'s adapter only produces
evidence and blocks until the node calls back; but per the node corpus an open
position forces verdict `unknown` (PE-7), so B's command pipe is dead for as long
as any position is open after any UNKNOWN — a livelock the spine never addresses.
**Severity: high.**
**Clause:** CT-20 pins the resolution protocol. The adapter produces evidence and
**never clears its own block**. Unblocking is an explicit typed
`resolve_unknown(command identity, resolution ∈ {observed-accepted,
observed-absent, operator-attested})` call whose caller is the node; the
resolution is itself an observation record. The block is **per command**, cleared
by resolution — never per account, cleared by verdict — so an account-level
`unknown` verdict does not freeze the pipe.

### H-09 — A failed secret store after rotation is "an alarm" only; one adapter keeps trading into a guaranteed lockout

AD-26: "where a venue rotates refresh material on use, the new secret is stored
before the old is discarded — a failed store after rotation is **an alarm**."
An alarm is not a refusal and not a block. **Unit A** honors this verbatim and
keeps trading with a rotated-but-unstored token: at the next restart the stored
(now venue-invalidated) material fails and the live account is unreachable,
mid-position. **Unit B** treats it as `unavailable dependency` and blocks new
commands, by analogy to AD-27's unpersistable-journal rule. Both cite the spine.
**Severity: high.**
**Clause:** align with AD-27's pipe split — a failed store after rotation is an
alarm **and** a command-pipe block (`unavailable dependency`, after-condition =
successful store or operator re-provision); the sensing pipe is unaffected. Old
material is never discarded before the store confirms; where the venue has
already invalidated it, the session is marked degraded and the AD-26 compromise
drill is triggered.

### H-10 — AD-26's own first sentence is false for the connection manager, and the two repairs have different blast radii

AD-26 opens: "QMF components handle **secret references** (typed names), never
values; values are injected at the composition root." It then makes the CM "the
sole owner of token refresh" and requires it to **store** rotated material — both
of which require the CM to hold values and to write to the protected store.
**Unit A** has the root inject a `SecretValue`; the CM refreshes in memory and
storing is the root's job through a callback the spine never names — so AD-26's
store-before-discard rule cannot be honored at all. **Unit B** has the root inject
a `SecretStore` port (read + write); the CM reads, refreshes, and writes — which
puts long-lived secret values and write access to the credential store inside the
edge module AD-26 exists to keep them out of.
**Severity: high.**
**Clause:** carve the exception explicitly. The connection manager is the
**single named component permitted to hold secret values in memory**, for the
lifetime of a session; it receives a core-defined `SecretStore` port (read +
atomic replace) injected by the root, never raw values. Values never cross back
out of the CM — no getter, no logging, no refusal context, no health report, no
metric label. Every other component handles references only.

### H-11 — The adapter is told to emit registry records it cannot import, and the fingerprint consumers cite is ambiguous

AD-28: the adapter "emits instrument/account metadata snapshots as **registry
records** — AD-22's typed configuration inputs". AD-2: records/lifecycle for
shared nouns are **owned by `qmf-registry`**. Default-deny: `qmf-venue` may import
only `qmf-core`, so the adapter cannot import the record schema.
**Unit A** puts the snapshot type in `qmf-core` as a shared noun (arguably legal
under AD-2) and computes its `fp1` in the adapter. **Unit B** returns a
stdlib-typed mapping at the boundary (AD-19's precedent) and the root builds the
registry record, computing `fp1` after adding header fields. The two fingerprints
differ for identical market facts — and AD-22 makes "the registry record's
fingerprint … identity-bearing" for every indicator configured against it. Two
adapters, two identities for one instrument metadata snapshot, propagating into
every downstream result label.
**Severity: high.**
**Clause:** state the general edge-module rule once. Every artifact an adapter
produces is defined as a **`qmf-core` value type** (fingerprintable content); the
registry record wrapping it is minted by the root through `qmf-registry`; and
**the fingerprint consumers cite is the content fingerprint** — computed by
`qmf-core`'s single implementation — never the record fingerprint. This settles
AD-25's structure-emission pattern the same way.

### H-12 — Rate limits are per-connection but streams are per-account, and no rule gives protection commands priority on a shared throttle

Venue fact A4: 50/5 req/s **per connection**; AD-28 makes "accounts per
connection" a declared capability. So a throttle is shared across independent
command streams. **Unit A** implements one token bucket per connection (correct
per the venue facts), so a `close_all` on account X queues behind account Y's
order burst. **Unit B** divides the connection budget by declared accounts-per-
connection — "the adapter's declared conservative window model", also conformant
— trading throughput for isolation. AD-28 lists protection primitives
(suspend-new / drain / `close_all`) as capabilities but states no dispatch
priority anywhere, so a flatten can sit behind 200 queued orders.
**Severity: high** (money loss, not merely divergence).
**Clause:** CT-18 declares the throttle's **scope** (`connection | account |
binding`) as a required field. CT-19 declares a two-class dispatch priority:
protection commands (`cancel_order`, `close_position`, `close_all`) are dispatched
ahead of `place_order` on every shared throttle, and `suspend-new` takes effect
locally the instant it is invoked, with no venue round-trip. Queue discipline is
declared, never implicit.

### H-13 — One venue event lands in three AD-19 rooms with no stated write order or atomicity

AD-19's rooms include raw archive, journal, and the registry room. A single venue
event produces a raw payload (raw archive), a derived observation and journal
events (journal), and sometimes a metadata snapshot (registry room). AD-27
addresses only "an unpersistable journal event is a typed refusal that blocks new
commands" and says nothing about partial writes. **Unit A** writes raw first then
journal; **Unit B** journal first then raw. Either way, a failure between the two
leaves the rooms permanently disagreeing, and no rule says which is authoritative
at read time. The node corpus already ratified atomic state+evidence commit
(K-10); the spine did not inherit it.
**Severity: high.**
**Clause:** CT-20 declares the write as a single ordered unit with a named
transaction boundary the sink protocol must provide (declared `atomic` or
declared `ordered-with-recovery`), names which room each artifact lands in, and
makes a partial write a `storage failure` refusal that blocks the command pipe
and is itself journaled on recovery.

### H-14 — UNKNOWN is a state with no writer: minted as an observation, or inferred at read time from a node constant?

**Unit A** mints an explicit UNKNOWN observation at the local wall instant of the
timeout. **Unit B** writes nothing — UNKNOWN is the *absence* of a terminal
observation, computed at read time against the timeout policy in force. B's
evidence is then uninterpretable without a live configuration value, and the
timeout constant is node territory under the do-not-default standing, so the
meaning of B's stored evidence changes when the node is retuned. That breaks
replay determinism for the whole order path.
**Severity: high.**
**Clause:** UNKNOWN is minted as an **explicit observation record** carrying the
trigger (`timeout | transport-error | disconnect`), the monotonic elapsed
measurement, the wall receive instant, and **the declared timeout bound that was
in force**. The read-time fold never consults live configuration.

### H-15 — Automatic session recovery versus "QMF never auto-retries"

AD-27: "No QMF component retries, assumes an outcome, flattens, or invents
terminal state"; AD-28 and AD-26 simultaneously give the CM ownership of
reconnect, gap recovery, and token refresh, and AD-27 itself says "even a no-gap
reconnect emits correlation evidence" — presupposing automatic reconnection.
**Unit A**'s CM auto-reconnects with backoff. **Unit B**'s CM refuses to reconnect
without an explicit call, because reconnecting is retrying. One adapter is
self-healing and one is not; the node's supervision design differs accordingly.
**Severity: high.**
**Clause:** distinguish the two explicitly. **Session recovery** (connect,
reconnect, heartbeat, token refresh, gap replay) is CM-owned, automatic, governed
by injected constants under the do-not-default standing, and **never resubmits a
command**. **Command retry** remains prohibited. Every reconnect increments the
session epoch (H-07) and emits correlation evidence; in-flight commands become
UNKNOWN and stay UNKNOWN until resolved per H-08.

---

## 4. Medium — real divergence, cheap to close

### M-01 — "cTrader" is a platform, not a broker; AD-9's amendment can be read to void AD-26/27/28's cTrader clauses

The AD-9 amendment says "**no rule anywhere may name a specific broker**", and
AD-26/27/28 name cTrader in rule text five times. A builder reading cTrader as a
broker treats every such clause — including the first-connection verification
suite AD-28 calls "a named part of the adapter contract" — as non-binding
illustration; a builder reading it as a protocol family treats them as
requirements.
**Clause:** state in AD-9 that broker/venue legal identity and platform/protocol
family are distinct; the prohibition binds VenueIds and broker entities, while
platform-family clauses (cTrader, FIX, CCXT) are legitimate adapter-scoped
contract surface. Relabel the cTrader clauses "cTrader-platform adapter profile".

### M-02 — CT-20 must explicitly declare its AD-10 display-only exclusions, or AD-10 and AD-8 contradict each other on the same record

AD-10 makes every field identity by default and requires exclusion to be "an
explicit, versioned declaration in the contract — never an implementer's judgment
call." AD-8 requires the monotonic reading to be "excluded from identity", and
AD-21 requires `correlation_id` to be excluded. If CT-20 forgets to declare them,
the two rules contradict and two implementers resolve it opposite ways.
**Clause:** CT-20 ships an explicit exclusion list — receive-monotonic value,
boot epoch id, session epoch id, `correlation_id`, occurrence facts — as versioned
contract surface, mirroring AD-21's `correlation_id` precedent.

### M-03 — Verification assertions are journaled as "`data quality` / `control action`" — the slash is a fork

AD-28 leaves the choice open, so one adapter's feed-health rows are invisible to a
consumer filtering the other's category.
**Clause:** pin per class — measurement and verification results → `data
quality`; adapter-initiated state changes (suspend-new, drain, session restart,
throttle engaged, reconnect) → `control action`. Exhaustive table in CT-18/CT-20.

### M-04 — A proto tag change bumps "AD-5's second ladder" — but which contract's format version?

**Unit A** bumps CT-18 only; **Unit B** bumps all four CT-18…CT-21. Since AD-12
puts the contract format version into every result label, B's proto bump changes
the identity of every observation and A's changes none.
**Clause:** the venue protocol artifact identity is a field of the **capability
declaration** (H-03's artifact 1) and enters only that record's fingerprint. A tag
change mints a new capability declaration plus re-verification; it bumps a CT-*
format version only where the wire change alters that contract's public shape.

### M-05 — Venue-native ids inside a command's `fp1` are not qualified

`close_position` targets a venue-minted position id. AD-9 guarantees VenueIds are
never reused; nothing says venue-native position or order ids are not. A recycled
position id with the same quantity and instrument yields the same `fp1` and is
therefore an "idempotent accept" of an economically different close.
**Clause:** every command's `fp1` includes the (VenueId, account) qualification,
the session epoch, and the caller's sequencer ordinal; a venue-native id is never
sufficient on its own. A resend carries the identical ordinal, preserving
idempotency.

### M-06 — The "three-outcome law" enumerates four outcomes

A naming defect with real cost: it is the sentence H-02's two builders argue over,
and it invites the reading that `denied-locally` is not really an outcome.
**Clause:** rename to the **four-outcome law**, or state in-band that
`denied-locally` is the fourth, local outcome and that the three venue outcomes
are those reachable only after submission.

---

## 5. Cross-cutting note — three cures already paid for that the venue increment does not inherit

Worth calling out as a pattern rather than a finding, because it predicts where
the next venue defect will be:

1. **AD-25's read-time fold** — bought to stop "a mutable state machine sitting on
   the immutable store". AD-27's order-state machine is exactly that shape (C-03).
2. **AD-10's collision split** — byte-identical accepted, differing bytes refused.
   It assumes byte-identity implies meaning-identity, which secret-reference
   names (C-06) and display-only fill prices (C-07) both break.
3. **AD-7's named conversion boundary** — written for floats crossing back to
   Money/Price/Quantity. AD-7's *foreign-money* clause then speaks only of
   integers, leaving the single most important venue float — the execution price
   — outside the discipline (C-07).

Each of the three is closed by the clauses above, but the pattern suggests a
standing check for future sittings: **when a new AD introduces a state, an
identity, or a foreign value, name which earlier AD's cure applies to it.**

---

## 6. What is genuinely strong

Stated so the gate is not read as a rejection:

- The UNKNOWN-as-a-state ruling, the no-retry/no-invented-terminal-state rule, and
  the command-pipe-versus-sensing-pipe split are correct and are the hardest
  things to get right in an order path. They match the node corpus without
  importing node authority.
- Fixing the vocabulary at four kinds and refusing `amend_order` through an opaque
  payload closes the corpus's own T-18 tension at the architecture layer.
- Making the first-connection verification suite part of the adapter contract —
  rather than a runbook step — is the right home for venue-facts bundles B and C.
- AD-26's store-before-discard rule and the compromise drill are more than most
  systems ever write down; the gaps found here (H-09, H-10) are about who blocks
  and who holds, not about the rule being wrong.
- The neutral-port/capability-record shape does what it claims: nothing
  venue-shaped reaches `qmf-core`, and a CCXT-class adapter really can slot in —
  once C-01, C-02, C-04, and C-09 stop letting it slot in *differently*.
