---
review: adversarial
lens: ADVERSARY — attack the spine as a consistency contract for independently-built units
target: ARCHITECTURE-SPINE.md (Trading Node, 737 lines, TN-1..TN-24) + .memlog.md (45 entries, A1-A30)
reviewer: independent Opus seat, reviewer gate
date: 2026-08-28
verdict: CONDITIONAL PASS — the spine is unusually complete on law and vocabulary, but it does not yet close enough seams to be safe as a build substrate for independently-built epics. 7 critical and 9 high holes let two units obey every TN to the letter and still build incompatibly, and four of them can move or trap real money.
---

# Adversarial review — Trading Node architecture spine

## Method

The spine's stated job is a **consistency contract for independently-built units one level down** (epics → stories → factory-coded stories, each built in its own worktree by an agent that reads the spine and little else). The adversarial test is therefore not "is a rule wrong" but:

> **Can I construct two units that each obey every TN sentence to the letter and still fail to compose?**

I constructed twelve such pairs. Each pair below is a hole: the divergence is *permitted* by the current text, so two epics will land it, and it will only surface at integration or — worse — on the money path at the soak. For each I give the exact **Rule sentence to add or tighten**, phrased so it can be pasted into the named TN.

I also ran the money-path classics the brief names: a float slipping in through equity derivation or drift decomposition (**C7 — found**); a timeout read as rejection in TN-6/10/11 (**H8 — a near miss found: a pacer-queued command minting UNKNOWN**); an automatic de-escalation reachable through a clocked clear (**C6 — found**); a control that can block an exit (**C1 and C2 — found twice**); a replay artifact reaching a live room (**H7 — found**); a demo credential path that could refresh the live token (**C3 — found, and it is the sharpest finding in this review**).

**Vocabulary policing: CLEAN.** `grep -nEi '\b(engine|kernel|plugin|plugins|exam|minimal core|paper node)\b'` over the spine returns two hits, both of which are the spine forbidding the term (TN-1 line 121, Consistency Conventions line 571). "The trading node" is used as one product with modes `paper | live` throughout; no "paper node", no "the paper node's loop", no "engine". The Naming convention row is the strongest single row in the document and should survive verbatim into the doc-factory increment.

**What is genuinely strong** (stated so the findings are read in proportion): the four-verdict reconciliation correction; the veto/suppression paths as first-class outputs; `composition_fp` sealed into the boot epoch so every evidence row is traceable to its composition; the refusal to mint a fourth control-window kind for venue maintenance; "an alert is evidence, not permission"; RTO measured never declared; the explicit L30 reconciliation note handed to the doc factory rather than settled silently; and the A1-A30 register, which makes every without-operator call individually overturnable. None of the findings below touch those.

---

## CRITICAL

### C1 — Four blanket command-pipe blocks are minted, against the inherited invariant that forbids them. An exit can be blocked.

**Where:** TN-10 ("Startup reconciliation gates the COMMAND pipe only"); TN-12 ("a failed store after rotation raises an alarm and blocks the command pipe while sensing continues"); TN-24(h) ("a partial write is a storage failure that blocks the command stream"); Ports table, `ObservationSink/JournalSink/RecordSink` row ("unpersistable blocks the command stream"). Against the Inherited Invariants row for **L39**, quoted in this spine at line 89: *"exit preservation: the blocking half of any control is entries only; **no blanket command-pipe block may be minted**."*

**What:** the spine binds L39 in the inherited table and then mints four blanket command-pipe blocks in four different TNs, none of which carves out exits, protective closes, `cancel`, or a risk-non-increasing `amend_protection`. TN-14 does it correctly ("effects are entry-side only per L39"); TN-8's dead zones do it correctly ("entries pause; exits, safety acts and data streaming are never blocked"); TN-10, TN-12 and TN-24(h) do not.

**Pair that breaks:** *the reconcile epic* vs *the order-path epic*. The reconcile epic implements TN-10 literally — until the startup read-back returns a verdict, the command stream refuses every command. The order-path epic implements L39 literally — an exit always passes. Both are correct against the text they were given. Whichever lands second wins, silently.

**Why it matters:** the failure case is a running position at boot, a slow or `out-of-lookback` read-back, and a stop that the node now cannot move or close. TN-7's answer ("a dead node is answered by the venue-resident protective stop") does not apply: the node is alive, it just refuses. The same shape recurs in TN-12: a rotation-store failure — a bookkeeping fault — locks the exit path, which is precisely what TN-24 says it prevents ("a bookkeeping fault turning into a market action" — here, a bookkeeping fault preventing a market action).

**Fix — add to TN-6 as a top-level rule sentence, and cross-reference it from TN-10, TN-12 and TN-24(h):**
> Every block the node can raise on a command stream — startup-reconciliation gating, a rotation-store failure, an unpersistable sink, a partial write, an outstanding UNKNOWN, or stand-down — is an **entry-side block only**: it refuses `place_order` and any risk-increasing `amend_protection`, and it never refuses `cancel`, `close_position`, `close_all`, or a risk-non-increasing `amend_protection`. A block that cannot be applied entry-side only is not minted. Where the venue path itself is unavailable, a protective command becomes a standing protection intent under TN-7 rather than a refusal.

---

### C2 — Stand-down-alive blocks the operator's flatten. Three rules say incompatible things about the same act.

**Where:** TN-4 ("past it BOOTS INTO STAND-DOWN: **sequencers refuse-and-journal**, adapters quiesce and drain, the doors keep serving so resurrection stays reachable"); TN-17 (powers channel "flatten at any scope … **reachable in stand-down**"); TN-8 ("Flatten authority — **operator at any scope, always**").

**What:** in stand-down the sequencers refuse everything and the adapters have quiesced and drained. The doors still serve, so the operator can *press* flatten — and the sequencer refuses it, or the session is closed and there is nothing to submit to. TN-17's "reachable in stand-down" is satisfied by the door answering; it is not satisfied by the flatten happening.

**Pair that breaks:** *the host/supervision epic* (TN-4) vs *the doors epic* (TN-17). The host epic ships stand-down as a total sequencer refusal because TN-4 says so. The doors epic ships flatten as always-passing because TN-8 says "always". Integration produces a node that journals an operator flatten as `suppressed` and does nothing.

**Why it matters:** stand-down is entered exactly when things are worst — a crash loop, a halt-band clock breach, a preflight failure. It is the state in which the operator most needs the one authority the whole spine reserves to them. As written, the node's safety state disarms the operator's safety control.

**Fix — add to TN-4's stand-down bullet:**
> In stand-down the sequencers refuse and journal **bot-minted and Book-minted intents**; operator-signed protective commands (`flatten` at any scope, `close_all`, `cancel`, and risk-non-increasing `amend_protection`) and the standing-intent dispatcher always pass. Where the adapters have quiesced, an operator protective command is journaled as a standing protection intent before dispatch under TN-7 and is satisfied on the next healthy session — it is never refused and never dropped. "Reachable in stand-down" means enactable, not merely answerable.

---

### C3 — One cTID credential serves both connections, and the refresh duty is keyed by connection. The demo/soak path can burn or rotate the live session's token.

**Where:** TN-11 ("Connections are keyed by `(venue, environment)` — one demo plus one live … Session duties run on the node scheduler (TN-4)"; the five duties include "token refresh"); TN-12 ("the bootstrap credentials: client id and secret, **the initial access and refresh tokens**, and the cTID account ids"; "the refresh token **dies on use**"; "after provisioning the VPS session is the ONE live refresher"); TN-12's wizard "fetches the `ctidTraderAccountId` list **from the access token**". Ledger row cited at line 97: "exactly one live refresher per credential (`:49`)".

**What:** the spine's own text establishes that a *single* access/refresh token pair enumerates the cTID accounts — i.e. one credential covers **both** the demo and the live account under that cTID. The spine then places token refresh among the per-adapter `SESSION_DUTIES` and gives the node scheduler two sessions to drive. Nothing in TN-11, TN-12 or TN-4 says the refresh duty is keyed by **credential reference** rather than by connection, or that at most one refresh may be in flight per credential.

**Pair that breaks:** *the venue-transport epic* (builds a session object per `(venue, environment)`, each running its own duty set — the only reading TN-11 supports) vs *the secrets epic* (builds `SecretStore` read + atomic replace with store-before-discard, per credential reference — the only reading TN-12 supports). Both correct. Composed: two sessions, one credential, two refresh duties. The demo session refreshes at T; the refresh token dies on use; the live session's duty fires at T+ε with the dead token, gets an invalid-grant error, and — under TN-11's unmapped-code default — mints `(transient venue failure, retryable = no, outcome = UNKNOWN)` and an alarm. The live session is now unauthenticated with an outstanding UNKNOWN blocking its stream, caused entirely by the demo side.

**Why it matters:** this is the brief's "demo credential path that could refresh the live token", and it is live in the current text. It fires during the soak — the exact milestone where the demo connection is running the full machinery — and its blast radius is the live session. It also silently violates the ledger's "exactly one live refresher per credential", which the spine cites but never operationalizes. The consequence at the far end is a live account the node cannot reach while positions are open.

**Fix — add to TN-12 (and cite from TN-11's session-duties sentence):**
> Token refresh is keyed by **credential reference, never by connection**. At most one refresh is in flight per credential reference; every session sharing that credential is a reader of the rotated access token, not a refresher. The refresh duty is owned by the connection manager as a whole (not by a session), executes store-before-discard against `SecretStore.atomic_replace`, and on success republishes the new access token to every session bound to that credential before any of them reissues a request. Whether the demo and live environments share one cTID credential is a **declared roster fact per credential reference**, verified at preflight; a roster that declares two credentials runs two independent refreshers, and a roster that declares one runs exactly one. An authentication failure attributable to a rotation in flight is a retry-after-refresh condition, never an UNKNOWN.

---

### C4 — Book mode is owned twice. A restart can flip a Book the operator put into PAPER back to LIVE.

**Where:** TN-18's layer list places a **Book fragment** in the sealed resolved config artifact; TN-9 says paper is "a Book-level mode … expressed as **a dated binding-epoch change**" (a record); TN-10 step 7 lists "**Book modes**" among the read-time folds of the protection-state projection; TN-17 lists "**paper flip**" as a powers action, listed *separately from* "settings edit, which mints a new config version and schedules a restart at a safe point"; TN-15 exports "Book modes" as a protection metric; TN-2 seals the composition for the boot epoch.

**What:** the spine gives Book mode two owners and never states precedence. TN-18 puts it in the sealed artifact; TN-10 puts it in an append-only fold. TN-17 makes "paper flip" a *different* powers verb from "settings edit", so a flip does **not** mint a config version.

**Pair that breaks:** *the config epic* (compiles the Book fragment into the sealed artifact and composes Books at their declared modes, per TN-18/TN-2) vs *the paper epic* (mints a dated binding-epoch record and folds mode at read time, per TN-9/TN-10). Sequence: operator flips Book B to PAPER through the powers door → record minted, fold reports PAPER, metric reports PAPER. Next restart-at-safe-point (a settings edit elsewhere, a `deploy switch`, a crash-loop recovery) → the config epic composes Book B from the sealed Book fragment, which still says LIVE. Book B is now trading live money on a mode the operator explicitly left.

**Why it matters:** this is the highest-consequence instance of a class that recurs three times in the spine (see H5 for seat state and binding state). It converts a routine restart — which TN-16 calls always safe ("journal projections make any restart safe") — into an unannounced re-arming of live exposure. It also silently defeats TN-20's "approval never equals exposure", because exposure re-appears with no act at all.

**Fix — add to TN-18 as a partition rule, and mirror the sentence in TN-9 and TN-10:**
> The resolved node-config artifact declares **eligibility and identity only** — which Books and bots exist, which bindings are permitted, which values are resolved. It **never carries runtime state**. Book mode, binding state, seat state, standing intents, KSA level, bench counts, exposure and budgets are exclusively read-time folds over append-only records; the config compiler refuses any layer that supplies one of them. A restart therefore never changes a runtime state, and the composition can be sealed without freezing anything the operator can change while the node runs.

---

### C5 — Two sequencers, and one of them resets every boot. The command identity can be reused.

**Where:** TN-6 command mint ("`fp1` identity including `(VenueId, account)`, the **session epoch**, and the **node-owned sequencer ordinal**, mapped into `clientMsgId` at 100 characters or fewer, **injectively**"); TN-22 (the command-stream object "carries its own UNKNOWN block, `WriterId`, **gapless sequence**, control-rank table and pacer bucket"); TN-2 / inherited AD-21 ("`journal.sequence` is **gapless per (writer, boot-epoch)**"); Ports table `WriterSequencer` / `next_command_key` ("The node owns the sequencer"); TN-15 alarm list includes "**reused command identity**".

**What:** the spine names two counters in adjacent sentences and never separates them. The journal sequence is *defined* to be gapless per `(writer, boot epoch)` — i.e. it restarts at each boot. The command ordinal must be injective into `clientMsgId` **forever**, because an outstanding command from before a restart is still live at the venue. TN-22 puts both a `WriterId` and "gapless sequence" on the same command-stream object and does not say which is which; TN-6 says the command identity includes the *session* epoch, while the journal sequence is scoped to the *boot* epoch — and the Naming convention insists boot epoch, session epoch and binding epoch are "three ids, never merged", which makes the conflation more likely, not less.

**Pair that breaks:** *the order-path epic* (reads TN-22, uses the command-stream object's one gapless sequence for the command ordinal) vs *the host epic* (reads AD-21/TN-2, resets that sequence at each boot epoch because CT-13 requires it). Composed: after a restart the ordinal restarts at 1. A reconnect with an in-flight order from the previous boot now has two commands whose `clientMsgId` differ only by the session epoch — and TN-6 permits the mapping to be either injective *or* "through a durable command-id-binding record", the second of which an implementer will build keyed on the ordinal.

**Why it matters:** a reused command identity at the venue is a duplicate order or a mis-matched response — the exact defect TN-15 lists as an alarm and TN-24(b) as a data-quality event. It is reachable through the single most common node event (a restart), and it is invisible in paper until the demo server happens to redeliver.

**Fix — add to TN-6, and tighten TN-22's bullet:**
> The **command ordinal** and the **journal sequence** are two distinct counters and are never the same object. The journal sequence is gapless per `(writer, boot epoch)` and restarts at each boot epoch (CT-13). The command ordinal is monotone and **never reused across the life of a `(VenueId, account)` command stream**; its persistence across boot epochs is a durable property of the stream, recovered at boot before the sequencers open (TN-10 step 9). `clientMsgId` injectivity is proven over `(VenueId, account, session epoch, command ordinal)`, and a boot that cannot recover the previous ordinal high-water mark refuses to open the sequencers rather than restarting the count.

---

### C6 — The KSA fold can automatically de-escalate through a clocked reconciliation tick.

**Where:** TN-7 ("automatic transitions **ESCALATE ONLY**; de-escalation is an operator `resume` only (A1)"; "the KSA level is a **read-time fold over the control-action stream** (AD-36 fold contract; **most-restrictive on ambiguity**)"; "`drain` and `close_all` become STANDING PROTECTION INTENTS … **satisfied only on a `reconciled` verdict**"); TN-10 ("Reconciliation cadence (node value): after every UNKNOWN, on every reconnect, at each accounting rollover, **and on a configurable periodic tick**"); TN-20 ("Clocked mechanical clears … mint CT-24 transitions only, never a CT-30 `resume`").

**What:** TN-20 correctly forbids the *obvious* clocked de-escalation. The reachable one is subtler and the spine leaves it open: the level is a fold whose contract is "most-restrictive on ambiguity", and the trigger classes include `connectivity` and `unknown_state` — conditions that **clear on their own**. Nothing in TN-7 states that the fold is monotone with respect to escalation records. The natural implementation of "most-restrictive over the currently-ambiguous set" is `max(level over active triggers)`, and a trigger stops being active when the periodic reconciliation tick returns `reconciled`, satisfying the standing intent and resolving the UNKNOWN.

**Pair that breaks:** *the protection epic* (builds the KSA fold as most-restrictive over live trigger conditions — a defensible reading of AD-36's fold contract, and the only one that makes "most-restrictive on ambiguity" mean anything) vs *the reconcile epic* (builds the periodic tick that clears `unknown_state` and satisfies standing intents, exactly as TN-10 and TN-7 instruct). Composed: a `connectivity`-triggered RED, a reconnect, a periodic `reconciled` verdict at 03:00, and the level is GREEN at 03:00:01 with no human anywhere. The node resumes entries.

**Why it matters:** it is the brief's named classic and it defeats TN-7's stated Prevents ("an automatic de-escalation") through a path TN-7 itself creates. It fires unattended, overnight, which is precisely the operating mode the PRD's unattended-operation doctrine assumes.

**Fix — add to TN-7's fold bullet:**
> The KSA fold is **monotone non-decreasing within a level epoch**: it takes the maximum over every escalation record in the stream and **lowers only on an operator `resume` record**, which opens a new level epoch. Resolving a trigger's underlying condition, satisfying a standing protection intent, a `reconciled` verdict, a reconnect, a clocked clear, a restart, or the absence of new escalations **never lowers the level**. "Most-restrictive on ambiguity" governs which level an ambiguous escalation resolves to, never whether a level decays.

---

### C7 — Equity derivation and drift decomposition have no declared arithmetic domain, under an epsilon-0 comparison. A float enters the money path here.

**Where:** TN-11 ("**EQUITY DERIVATION** — balance plus per-position unrealized P&L using the venue's own converted figures with `converted_by = venue` provenance, no QMX conversion (K-54)"); TN-10 ("broker-versus-virtual divergence decomposes into named journaled components … **`reconciliation_epsilon = 0`**; any non-zero residual sets `operator_review`"); Consistency Conventions ("Money is exact scaled integers; **the sole sanctioned float crossings are the declared venue decode and the declared comparison-rule quantize**"); TN-23 names "equity derivation, drift decomposition" as mutmut-covered money-path modules; parts-bin red flag: "one governed float crossing at `ctrader.py:423`"; TN-10's five first-connection checks include a **money exponent** check.

**What:** the spine declares the *invariant* (exact scaled integers) and the *inputs* (venue-converted figures) but never declares the **arithmetic domain of the sum**. Equity is a sum across N positions of venue-supplied converted figures; the venue supplies a per-message money-digits exponent, positions may carry different exponents, and the account balance carries its own. Nothing says the sum is performed as exact integers at a single declared exponent, what the rounding rule is when exponents differ, or what happens when a position's converted figure is absent or arrives at an undeclared exponent. TN-10 then subtracts four named components from that number and compares the residual to **zero**.

**Pair that breaks:** *the venue epic* (implements equity as `balance + Σ unrealized`, taking each figure through the one governed decode crossing — and the decode crossing is the sanctioned float, so the natural composition is a float sum) vs *the reconcile epic* (implements `residual = broker_equity − virtual_equity − Σ explained` and compares to exactly 0, because TN-10 says epsilon is 0). Composed: an epsilon-0 comparison over a float-derived left-hand side. Every rollover produces a non-zero residual of ~1e-15, every rollover sets `operator_review`, and the first implementer to notice will add a tolerance — silently converting `reconciliation_epsilon = 0` into a number nobody ratified, inside the one control that detects money going missing.

**Why it matters:** this is the brief's "float slipping in through equity derivation or drift decomposition" and it is present in both halves at once. The failure is not a crash; it is either permanent alarm fatigue on the single most important safety signal, or an unratified tolerance on the money path.

**Fix — add to TN-11's equity bullet and cite it from TN-10:**
> Equity derivation is **exact scaled-integer arithmetic in the account's declared money exponent**. Each venue-supplied converted figure is decoded once through the declared decode crossing at **its own declared exponent** and re-scaled to the account exponent by exact integer arithmetic; no float participates in the sum, and a figure that arrives without a declared exponent, or at an exponent that cannot be re-scaled exactly, **refuses the equity derivation with a typed refusal** rather than approximating. Drift decomposition operates in the same integer domain, and `reconciliation_epsilon = 0` is a statement about that domain — a tolerance is never introduced to absorb representation error, because none exists.

---

## HIGH

### H1 — The pacer bucket has two owners. N accounts on one connection means N × the venue ceiling.

**Where:** TN-22 ("One **command-stream object** per `(VenueId, account)` carries its own UNKNOWN block, `WriterId`, gapless sequence, control-rank table **and pacer bucket** — the bucket keyed by the CT-18-declared `throttle_scope` (`connection | account | binding`)"); TN-11 ("the pacer stays below the declared 50 requests-per-second non-historical and 5 requests-per-second historical ceilings **per connection**"; "accounts multiplexed" over one connection); TN-13 (the history bridge uses "venue tick history (5 requests per second, one-week span cap)"); TN-4 (five session duties, including gap replay, run on the node scheduler); TN-10 (the reconciliation read-back issues venue requests).

**What:** TN-22 gives each command stream *its own* bucket; TN-11 states the ceiling is *per connection*; and four independent issuers share that connection — the order path, the session duties (heartbeat, gap replay, verification monitors), the history bridge, and the reconciliation read-back. Only the first is inside TN-6's priority ordering.

**Pair that breaks:** *the roster epic* (per-stream bucket, TN-22) vs *the venue epic* (per-connection ceiling, TN-11). Two accounts multiplexed on the live connection, each admitting below 50 rps, and the connection emits 100 rps. Separately: a gap replay after a reconnect saturates the bucket, and a `close_all` waits behind it — TN-6's "`cancel`, `close_position`, `close_all` and `amend_protection` are served ahead of `place_order`" orders the order path against itself, not against the duties.

**Why it matters:** the first half is a venue throttle or disconnect during exactly the reconnect storm that produced the gap replay. The second half is another instance of C1's shape — a protective command queued behind housekeeping.

**Fix — replace TN-22's bucket clause:**
> The pacer bucket is an object owned by the **connection**, instantiated once per declared `throttle_scope` (`connection | account | binding`) as CT-18 declares it. A command stream **admits through the bucket its declared scope names**; it never holds a bucket of its own. **Every** issuer on a connection — the order path, the five session duties, the history bridge and the reconciliation read-back — admits through the same bucket, and the bucket reserves a declared minimum capacity (a node value, do-not-default) for protective commands (`cancel`, `close_position`, `close_all`, risk-non-increasing `amend_protection`) that no other issuer may consume.

### H2 — `WriterId` has five minting sites and no allocation authority. A collision breaks CT-13 gaplessness.

**Where:** TN-3 (calendar recorder, backup and restore drill "all under distinct `WriterId`s"; sandboxes push "`WriterId`-scoped fragments"); TN-13 ("under the venue `WriterId` — machine, adapter role, `VenueId`, account"); TN-19 ("the node's composition root holds the `WriterId` for Bot-domain record streams"); TN-22 (the command-stream object "carries its own … `WriterId`"); Ports table (`StreamingIndicator.update()` feeder `WriterId` — "One holder per streaming instance on the live path").

**What:** five places mint or hold a `WriterId`, one gives a partial derivation tuple (TN-13's four fields), and nothing declares the namespace, the uniqueness proof, or who allocates. AD-21's `journal.sequence` is gapless **per `(writer, boot epoch)`** — so two components that derive the same `WriterId` each advance a sequence under one identity and produce interleaved ordinals that are, by construction, not gapless.

**Pair that breaks:** *the data epic* (mints the venue `WriterId` as `(machine, adapter role, VenueId, account)`, per TN-13) vs *the roster epic* (mints the command-stream `WriterId` for `(VenueId, account)`, per TN-22). Both derive from `(VenueId, account)` on the same machine with the same adapter; nothing forbids them colliding, and nothing tells either epic what the other used.

**Fix — add to TN-2's Compose act:**
> `WriterId` is **allocated exclusively at the composition root during Compose**, from a declared namespace, and handed to each writer; no component derives its own. The root proves the allocated set is pairwise distinct before Seal, journals the full allocation on the boot-epoch record alongside `composition_fp`, and refuses to boot on a collision. Every writer the node runs — the command streams, the venue recording feed, the Bot-domain record streams, each streaming-indicator feeder, and each timer unit — appears in that allocation.

### H3 — Three claimants on the first write of an inbound observation, and the accumulator has no durable cursor.

**Where:** TN-5 ("A **push-to-pull accumulator** sits between the venue edge and the loop: **every inbound observation is recorded and journaled FIRST** — recording precedes interpretation — then folded into the next slice"); TN-13 ("live ticks, bars and depth **enter as CT-10 source observations through qmf-data's CT-15 intake** into the LIVE world room"); TN-3 ("the connection manager's canonical sensing feed **IS the recorder**"). The two diagrams disagree with each other: the paradigm diagram routes `CM → ACC → LOOP`, while the process-internals diagram routes **both** `EDGE → ACC` **and** `REC → ACC`.

**What:** three sentences each make a different component the first writer of an inbound tick, and the spine's own two diagrams draw two different topologies for it. Separately, nothing declares the accumulator's **durable cursor**: TN-4's shutdown flushes sinks, but TN-10's nine-step boot has no step that re-folds observations that were journaled and never interpreted.

**Pair that breaks:** *the loop epic* (builds the accumulator as the journaling front door, per TN-5) vs *the data epic* (builds the CT-10 producer writing through CT-15 intake into the world room, per TN-13). Composed, one tick is written twice under two identities with two sequence ordinals — or, if each assumes the other did it, the world room and the journal disagree about what arrived.

**Why it matters:** "recording precedes interpretation" is the spine's evidence-integrity keystone; two implementations of it produce an evidence tier that cannot be replayed (TN-21 diffs against the recorded stream) and a `sequence gaps` metric that fires forever.

**Fix — add to TN-5's accumulator bullet:**
> The accumulator is the **single first writer** of every inbound observation: the connection manager hands raw decoded observations to the accumulator, which records them through the CT-15 intake into the live world room **and** journals them under the allocated venue `WriterId`, and only then makes them foldable. The recorder duty is a *role* of this one path, not a second writer, and no component writes an inbound observation anywhere else. The accumulator maintains a **durable interpretation cursor** in the journal; TN-10's boot order re-folds every observation recorded after the last committed cursor position **before** step 7's protection-state projection, so an observation recorded before a shutdown is never lost to interpretation.

### H4 — "Safe point" is used in five places and defined in none, and the shutdown contract mints no UNKNOWN for in-flight commands.

**Where:** "safe point" at TN-2 Seal, TN-16 (`deploy switch`), TN-17 (settings edit), TN-18 (versioning), Consistency Conventions Ops row — five uses, zero definitions. TN-4's shutdown contract: "SIGTERM causes `suspend_new` … then a flush of every sink … then sessions close **with no command resubmission**, then exit 0."

**What:** two units will define "safe point" differently (a slice boundary; a drained pacer; no outstanding UNKNOWN; no in-flight submission; a closed accounting boundary) and both will be right. Worse, the shutdown contract as written stops at `suspend_new` — which blocks *new* entries — and never addresses a command already at the wire whose outcome has not arrived. TN-6 owns "the submission deadline that mints UNKNOWN", but if the process exits before that deadline expires, **no UNKNOWN record is written**, and TN-10 step 5 ("resolve outstanding UNKNOWNs") has nothing to resolve. The stream opens at step 9 unblocked, with an order possibly live at the venue.

**Pair that breaks:** *the deploy epic* (safe point = drained pacer + slice boundary, per TN-16's "drain-aware") vs *the host epic* (safe point = the shutdown contract's four steps, per TN-4). Neither waits for command terminality; L35's "UNKNOWN blocks its stream" is bypassed by a restart.

**Fix — add to TN-4's shutdown bullet, and cite the definition from TN-2, TN-16, TN-17 and TN-18:**
> A **safe point** is a state in which (a) the slice driver is between slices, (b) `suspend_new` is enforced on every stream, (c) every command has reached a terminal outcome **or has had an UNKNOWN minted for it**, and (d) every sink has flushed with block-on-unpersistable honored. The shutdown contract reaches a safe point before exit: after `suspend_new` and before closing sessions, it **mints an UNKNOWN for every command without a terminal outcome**, journaled with its command identity, so L35's stream block survives the restart and TN-10 step 5 has the record it needs. A shutdown that cannot reach a safe point within the declared drain window mints UNKNOWNs for the remainder and exits non-zero.

### H5 — Seat state and binding state are owned twice, the same way Book mode is. Activation does not survive a restart.

**Where:** TN-19 ("the **roster** — which Bot `fp1` sits at which Book binding, and **each seat's state** — is **deployment configuration** plus AD-41 seat records"); TN-10 step 7 (folds include "**seat states**", "Book modes", "binding states"); TN-20 ("**ACTIVATION** … is a SECOND, separate operator action … journaled as its own transition" — with no config version minted); TN-22 (the roster lists bindings); TN-15 (metrics export seat states and binding states).

**What:** the same two-owner defect as C4, on three more entities. TN-19's "deployment configuration **plus** AD-41 seat records" is the ambiguity in one phrase: the config is sealed at boot, the records are folded at read time, and neither is declared authoritative.

**Pair that breaks:** *the seats epic* (composes seats at their config-declared states, per TN-19) vs *the promotion epic* (mints activation as a journaled transition and folds seat state, per TN-20/TN-10). Restart: an activated seat reverts to ADMITTED, or — worse in the other direction — a seat the operator benched returns `active` because the sealed roster says so. TN-20's stated Prevents is "an approval quietly becoming a trade"; here a *restart* quietly becomes a trade.

**Fix:** covered by C4's partition rule; additionally tighten TN-19's roster sentence:
> The roster in deployment configuration declares **eligibility only** — which Bot `fp1` **may** sit at which Book binding. A seat's state (`admitted | active | benched`) is exclusively a read-time fold over AD-41 seat records and CT-24 transitions, and the config compiler refuses a roster layer that supplies a seat state.

### H6 — The registry and the config artifact both claim to hold a variable's value. `ksa_effect_matrix` is in both lists verbatim.

**Where:** TN-18 ("Every node-minted variable is **registered in `docs/registry/variables.yaml` with `configurable: true`**, its unit-kind, its owner scope, and **evidence values**"; and, three lines later, "Do-not-default values are BLANK until ruled: … **`ksa_effect_matrix`**, window widths, clock bands …"); TN-8 (the same variables listed as "registry rows, evidence values only"); TN-7 (`ksa_effect_matrix` is "a `configurable: true` UI-editable node variable set … carrying NO spine value"); B-15 / TN-3 (the registry is read "through one registry-read port over **immutable as-of sets**" pulled from the passive hub); TN-17 (settings scopes: "system … **component (registry)** … instance values").

**What:** a node variable's resolved value has two homes — the versioned config artifact on the VPS (TN-18's compiler, TN-17's settings edit) and the registry as-of set read through `RegistryReadPort` (B-15, immutable, hub-mediated). The spine never partitions them, and `ksa_effect_matrix` appears in both lists by name.

**Pair that breaks:** *the config epic* (compiles values into the resolved artifact and lets the powers channel edit them) vs *the registry epic* (writes rows into `variables.yaml`, published as immutable as-of sets, read-only through the port per DEC-0165 "no second cache"). Composed: two values for the KSA effect matrix, and TN-17's "settings edit" writing the one nobody reads.

**Fix — add to TN-18:**
> `docs/registry/variables.yaml` declares a variable's **schema and nothing else** — unit-kind, `ui-editable` flag, owner scope, `admission_impact`, and recorded evidence values that are never resolved values. The **resolved node-config artifact is the sole home of a variable's resolved value**; the compiler refuses any key that has no registry declaration, and refuses to read a value from the registry. The powers channel and the CLI edit the config artifact only.

### H7 — Replay reads the live world room, which TN-21 itself calls a policy rejection; and `BotStateScope` may not carry `world`.

**Where:** TN-21 ("a REPLAY VENUE ADAPTER … feeding the recorded observations … **from the live world room**"; and, two bullets later, "**a cross-world read is a policy rejection**"); inherited AD-19 ("seven room-roles per world, **cross-world read refuses**"); Ports table (`BotStateScope` **four-tuple**, "cross-tuple restore refuses"); TN-19 (bot state "restored only within the same tuple").

**What:** TN-21 contains a flat self-contradiction — a `world = replay` run whose entire input is a read of the live world room. Two units will resolve it two ways: a sanctioned read, or a refusal that makes replay unbuildable. Separately, the spine never states that `world` is a component of `BotStateScope`; if it is not (the tuple is four fields and the spine names none of them), a bot-state snapshot produced by a replay run is restorable into a **live seat** — a replay artifact reaching a live room, through a door the spine believes it closed.

**Fix — add to TN-21:**
> A replay run reads sealed live-world observations through a **named one-way replay import port**, the single sanctioned cross-world read in the node; it is read-only, refuses any observation not yet sealed, and is the only exception to AD-19's cross-world refusal. Every artifact a replay run produces — decisions, folds, journals, **and bot-state snapshots** — carries `world = replay`; `world` is a component of the identity under which bot state is scoped and restored, so a replay snapshot can never be restored into a live or paper seat, and live state can never be restored into a replay run.

### H8 — The submission deadline has no declared start point. A command that never left the process can mint UNKNOWN and block its stream.

**Where:** TN-6 ("the **submission deadline that mints UNKNOWN** (`commands.py:47`, `:1167`)" among the node-owned do-not-default values); TN-6's pacer sentence ("the pacer stays below the declared … ceilings"); L35 as bound at line 85 ("a timeout is never a rejection; **UNKNOWN blocks its stream**").

**What:** the spine never says whether the deadline starts at **command mint** or at **wire handoff**, and never says what a `RatePacer.admit` refusal *is* — a refusal (a `decision` event on the veto path), or a wait. If the deadline starts at mint and a pacer refusal is a wait, a command that was never transmitted times out into UNKNOWN, which blocks the whole stream under L35 and forces an operator `resolve_unknown` for an order the venue never saw.

**Pair that breaks:** *the order-path epic* (starts the deadline at mint, because that is where the identity is minted) vs *the venue epic* (queues behind the pacer, because TN-6 says the pacer stays below the ceiling). This is the inverse of the classic the spine guards against: not a timeout read as a rejection, but a **local queue read as a venue timeout**.

**Fix — add to TN-6:**
> The submission deadline **starts at wire handoff** — the moment the connection manager transmits — and never at command mint. Time spent awaiting pacer admission is a **local queue**, measured and exported separately, and it never mints UNKNOWN. A pacer admission that cannot be granted within the declared local queue bound is a **typed refusal on the veto path** naming the pacer as the refusing door, not an UNKNOWN and not a stream block.

### H9 — The demo binding carries `world = live`, so TN-10's live drift check catches the binding TN-9 excludes.

**Where:** TN-9 ("the paper target is the paired demo account — **role `demo`, `world = live`**"; "the demo binding stays **excluded from the LIVE drift check**"; a demo residual "**ALARMS** for investigation rather than halting"); TN-10 ("**Unexplained LIVE drift** stands that binding down for entries … with no automatic resume"; "`reconciliation_epsilon = 0`; any non-zero residual sets **`operator_review`**"); TN-22 (bindings keyed `(VenueId, AccountId, role, world)`).

**What:** the discriminator between "the LIVE drift check" and "the demo drift check" is never named. The obvious key — `world` — is wrong, because TN-9 explicitly gives the demo binding `world = live`. The correct key must be `role`, and the spine never says so. Separately, `operator_review` appears exactly once in 737 lines and is never defined: is it a state that gates anything, or a label?

**Pair that breaks:** *the reconcile epic* (keys "live" on `world`, stands the demo binding down on the first demo-server quirk, and stalls the soak — the exact outcome A11 exists to prevent) vs *the paper epic* (keys on `role`, expects an alarm). And whichever way it lands, `operator_review` means "a gate" to one epic and "a flag" to the other.

**Fix — add to TN-10:**
> The live drift stand-down is keyed on the binding's **`role`**, never on its `world`: a binding with `role = live` stands down for entries on unexplained drift, and a binding with `role = demo` alarms at the live severity class and continues, whatever its `world`. `operator_review` is a **journaled binding-scoped state**, folded like any other, that gates the *next* live promotion or activation on that binding and gates nothing else; it never blocks the command stream, never blocks an exit, and clears only on an operator `resume` after a fresh reconciliation review.

### H10 — SQS reaches the Book door by two paths, and the baseline producer has no knowledge-time bound.

**Where:** TN-8 ("SQS — the V1 ratio sensor as a CT-16 configured producer, with the node as the **BASELINE PRODUCER from its own live tick recording**: one governed producer, published once, **consumed by the Book door**"); TN-19 (the MIS signal snapshot is "dispatched SYNCHRONOUSLY to a CLOSED consumer set: **the Book door** and the KSA. It carries the **per-instrument SQS score and hard-block flag**"); TN-6 (door order: "protection windows (CT-31), **SQS (AD-39)**, bench …").

**What:** two delivery paths for one number, and the spine says both are the one path. Separately, the baseline producer reads "its own live tick recording" — the world room the accumulator writes into (H3) — with no stated as-of bound, while the loop reads through surfaces that refuse look-ahead. A producer reading the world room "as of now" sees ticks the current slice has not folded.

**Pair that breaks:** *the protection epic* (SQS producer publishes to the door directly, per TN-8) vs *the MIS epic* (the snapshot carries the SQS score to the door, per TN-19). The door sees two SQS values at one instant and no rule says which wins — and the direct-read one is ahead of the slice frontier.

**Fix — add to TN-19 and cite from TN-8:**
> SQS reaches the Book door and the KSA **only inside the per-instant signal snapshot**; the sensor publishes into the snapshot and never to a consumer directly, so one instant carries exactly one SQS value. Every producer feeding the snapshot — the SQS baseline producer included — reads the world room **as of the slice's frontier instant only**, never as of wall-now; a producer that cannot be bounded to the frontier publishes `not_ready`.

### H11 — The SQS baseline's scope is unstated, so a demo-fed baseline may gate live money — or live may have no baseline at all.

**Where:** TN-8 ("the node as the BASELINE PRODUCER **from its own live tick recording**"; "**a live binding requires a present baseline**"); TN-9 (the soak includes "**SQS baseline minting**" — on the demo connection); TN-3 ("demo/paper evidence role-scoped within `world = live`", per the ledger at line 97).

**What:** the spine never says whether the baseline is keyed by `(VenueId, instrument)`, `(VenueId, environment, instrument)`, or `(VenueId, account, instrument)`. During the soak the only tick recording is the **demo** connection's.

**Pair that breaks:** *the protection epic* keying the baseline venue-wide → the live binding at go-live is gated by a baseline built entirely from demo-server ticks (a demo feed on the same venue is not the same feed: different liquidity, different spread behaviour, often a different tick cadence). *The venue epic* keying it by environment → at go-live the live binding has no baseline and TN-8 blocks it, discovering this at the end of the warm-up week.

**Fix — add to TN-8's SQS bullet:**
> The SQS baseline is keyed by `(VenueId, environment, instrument)`. A baseline conditioned on demo-environment ticks **never satisfies a `role = live` binding's present-baseline requirement**; the live binding's baseline is minted from live-connection recording during the warm-up week, and the soak checklist proves baseline *minting and blocking mechanics* on the demo environment, not the live baseline itself.

### H12 — Sandbox fragments and the promotion pull share the hub tree, and the one reverse crossing has no provenance refusal.

**Where:** TN-3 ("The **passive file-sync hub** (B-15) is a directory tree **on the VPS evidence tier**, pulled by the workstation over SSH and **pushed to by sandboxes** as `WriterId`-scoped fragments"; "Episodic sandbox plane (factory agents) — evidence carries `provenance = sandbox` and **never merges**"; "The only reverse crossing is the **click-gated promotion pull**"); TN-20 ("the crossing is a node-initiated pull of the registry as-of set from the hub, idempotent by artifact key").

**What:** the hub is simultaneously (a) part of the evidence tier that live evidence syncs into, (b) the inbox that sandboxes write into, and (c) the source of the one reverse crossing into the node. "Never merges" is asserted as a property of the *records* (`provenance = sandbox`) but nothing in TN-20's pull is stated to **check** it, and no directory or room separation is declared between the hub inbox and the evidence tier's live rooms.

**Pair that breaks:** *the data epic* (builds the hub as a writable directory on the evidence tier, per TN-3) vs *the promotion epic* (builds a node-initiated pull of the as-of set from the hub, idempotent by artifact key, per TN-20). Nothing in either refuses a sandbox-provenance artifact inside a pulled as-of set. This is the node's only inbound path and it is the one the operator's click authorizes.

**Fix — add to TN-3 and TN-20:**
> The passive hub is a **separate tree from the evidence tier's rooms**, with a write-only inbox for sandbox fragments and a read-only published area for as-of sets; the one-way evidence sync never writes into the inbox and the inbox is never a room. The promotion pull **refuses any artifact carrying `provenance = sandbox`** and refuses an as-of set containing one, verifying each artifact's `fp1` against the card before the seat lands ADMITTED; a refusal is journaled and alarmed, never skipped.

### H13 — A secret is held by three components, against an invariant that names one.

**Where:** TN-12 ("the connection manager, **the sole session owner and sole secret-value holder**"; and, in the same TN, "the object-storage/backup encryption key and the notification-channel token **ride the same store**"); Consistency Conventions ("Secrets travel by reference; **the connection manager is the only in-memory value holder**"); TN-13 (the backup runs under `qmn-backup.timer` — a **separate systemd unit**, needing the `PayloadCipher` key and rclone bucket credentials); TN-15 (the webhook `NotificationChannel` runs in the node's observability path, "service and token as config by reference"); TN-16 (`DynamicUser=yes` with `StateDirectory=qmn`, `LoadCredentialEncrypted` for every secret, across **four** units).

**What:** the invariant as written is false in the spine's own design. The backup unit is a different **process** that must hold the payload key and the bucket credentials in memory; the notification channel holds a token; only the venue session material is the connection manager's. Additionally, `DynamicUser=yes` gives each of the four units a distinct dynamic UID, and the spine never states how `StateDirectory=qmn` — which holds the AEAD-ciphertext rotated material under the KEK — is shared or scoped across them.

**Pair that breaks:** *the secrets epic* (builds `SecretStore` so that only the connection manager may read a value, per TN-12 and the Conventions row) vs *the data/backup epic* (needs the `PayloadCipher` key inside `qmn-backup.service`, per TN-13/TN-16). The secrets epic's design forbids the backup epic's requirement.

**Fix — restate the invariant in TN-12 and in the Conventions row:**
> Above the store, secrets travel by reference. **Venue session material** (client id and secret, access and refresh tokens) has exactly one in-memory value holder: the connection manager. Two further scoped holders exist and are named: the backup unit holds the CT-14 payload key and the object-storage credentials for the duration of one backup or drill run, and the observability path holds the notification-channel token; neither ever holds venue session material, and no other component holds any secret value. Each unit receives only the credentials its role names through `LoadCredentialEncrypted`; where units share `StateDirectory=qmn` under `DynamicUser=yes`, the shared-directory ownership and mode are declared in the unit files and verified by preflight.

### H14 — The kill line's scope is stated two ways in one bullet: per Book definition, and per binding.

**Where:** TN-8 ("**Kill line** — a **per-Book** capital floor `kill_line_capital_floor`, the SAME number as AD-40's `loss_floor`, **Book-declared**, blank blocks live … A breach auto-flattens **that binding's scope** … and stands the Book down"); TN-5 ("**Several Books on one account share** [the loop]"); TN-22 (the roster lists "the Book bindings on each" account — plural bindings per Book is not excluded).

**What:** "Book-declared, per-Book" and "that binding's scope" are two different scopes, and the spine never states the Book↔binding cardinality. If one Book definition may be bound at two accounts, the capital floor is ambiguous (per definition, or per binding?) and a breach at account A either does or does not stand the Book down at account B.

**Fix — add to TN-8's kill-line bullet:**
> A Book definition may be bound at more than one account binding. `kill_line_capital_floor` is **declared by the Book definition and evaluated per binding**, against that binding's own account capital; a breach flattens and stands down **that binding only**, and other bindings of the same Book definition are unaffected. Return is operator-signed per binding.

### H15 — The three timer units write journals with no boot ceremony, so `boot_epoch` and `composition_fp` are stamped two ways on one deployment.

**Where:** TN-3 ("Separate scheduled units run the news-calendar recorder, the nightly backup and the restore drill, all under distinct `WriterId`s"); TN-13 (the calendar recorder performs "idempotent intake"; backup and restore drill are "**both journaled as `data quality`**"); TN-2 (the four-act boot ceremony, `composition_fp` "stamped as occurrence provenance on **the boot-epoch record of every journal stream the node writes**"); inherited B-4 ("**the orchestrator owns all writes**"); AD-21 (gapless per `(writer, boot epoch)`).

**What:** three one-shot units write journal records twice daily or nightly. They do not run TN-2's ceremony, and they compose a *different, smaller* set (no venue adapter, no seats) — so if they compute a `composition_fp` at all it is a different value for the same deployment. And what is a one-shot unit's boot epoch: a new one per invocation (hundreds per year), or the long-lived node's?

**Pair that breaks:** *the data epic* (mints a fresh boot epoch per timer invocation, the only thing "boot epoch" can mean for a one-shot process) vs *the host epic* (treats `boot_epoch` as the node process's, per TN-2 and every metric and log field in TN-15). The evidence tier ends up with two boot-epoch semantics and two `composition_fp` values in one night's journals.

**Fix — add to TN-2:**
> A timer unit that writes journal records **runs an abbreviated ceremony**: it composes from the same resolved node-config artifact, computes `composition_fp` over **the same inputs as the node process** (so one deployment yields one value), mints its own boot epoch stamped with its unit role, and writes only under its own allocated `WriterId`. A timer unit that would need to compose anything the node process does not hands its work to the running node through the doors instead, honoring B-4.

---

## MEDIUM

### M1 — The crash-loop fold is blind to the most likely crash.
TN-4 folds "over **boot-epoch records**"; TN-2 writes the boot-epoch record during Compose/Fingerprint, i.e. **after** Preflight. A crash during Preflight (clock sync, credential store unreachable, disk) writes a typed failure but may never write a boot-epoch record, so the fold never counts it and stand-down never engages — systemd's `StartLimitBurst`, deliberately set *above* `(K, T)`, then becomes the only backstop, inverting the stated ordering. **Fix:** state that the crash-loop fold counts **boot attempts**, recorded as the first durable write of Preflight before any gate runs, not successful boot epochs.

### M2 — Preflight fail-closed contradicts stand-down-alive, and locks the operator out for K restarts.
TN-2's preflight is "fail-closed with a typed failure id, journaled"; TN-16 sets `Restart=on-failure`. So a failed preflight exits, restarts, exits — and the doors are **not** serving during any of it, which is the opposite of TN-4's design intent that "the doors keep serving so resurrection stays reachable". A clock-sync fault therefore makes the node unreachable exactly when the operator needs to flatten. **Fix:** state that a preflight failure **boots into stand-down-alive with the doors serving** rather than exiting; only a failure that prevents the doors themselves from binding exits non-zero.

### M3 — `resolve_unknown` has two issuance paths with no precedence.
TN-6 gives the node ownership of "the **issuance** of `resolve_unknown` with resolution in `observed-accepted | observed-absent` from the read-back — operator-attested only through the powers door"; TN-10 step 5 resolves outstanding UNKNOWNs automatically from the read-back; TN-17 lists `resolve_unknown` as an operator-attested powers action. Is the boot-time resolution automatic or operator-attested? TN-23's soak checklist says "an **operator** `resolve_unknown` clears it". **Fix:** state that a read-back that yields an unambiguous `observed-accepted | observed-absent` resolves the UNKNOWN automatically and journals the evidence; an ambiguous or absent read-back requires operator attestation through the powers door, and only that second path carries a signer identity.

### M4 — A connection fault maps to an unstated set of blocked streams.
TN-11 keys connections by `(venue, environment)` with accounts multiplexed; TN-22 keys the UNKNOWN block and the command stream by `(VenueId, account)`. A dead wire is a *connection* event affecting *N* streams, and the spine never states the mapping. **Fix:** state that a connection fault applies its effect to **every command stream bound to that connection**, enumerated from the roster at Compose, and that each affected stream journals its own block.

### M5 — Backup and restore-drill failures alarm in TN-13 but are absent from TN-15's closed allow-list.
TN-13: "failures alarming and never silently retried". TN-15: "the closed allow-list is the **ONLY** push tier", and neither backup failure nor drill failure appears on it. The two rules cannot both hold. Related: TN-14's clock-band breach alert is **soak-only** and "switch[es] off at go-live", so a live `no-new-entry` band breach produces no push (only `halt` is covered, via "stand-down"). **Fix:** add "backup or restore-drill failure" and "clock band breach at `no-new-entry` or worse" to the allow-list explicitly, or state that TN-13's and TN-14's alarms are console evidence and remove the word "alarming".

### M6 — The soak's required kill-line drill is unreachable as specified.
TN-23's checklist requires "a **kill-line breach on the paper Book** auto-flattens and stands down". TN-9 says "**Paper balance is family-scoped and frozen**". A frozen balance never crosses a capital floor, so the drill cannot fire in paper as written. **Fix:** state how the drill is injected — an operator-signed synthetic breach, or a paper capital floor evaluated against the paper ledger's running P&L rather than the frozen balance — and name which, since two epics will pick differently.

### M7 — Nothing binds the config version graph to the checkout commit.
TN-16's `deploy switch <commit>` changes distributions (hence `composition_fp`) without minting a config version; TN-18's version graph tracks config only. A rollback of the commit with a forward `current` config pointer produces a composition the dry-run never saw. **Fix:** state that `qmn deploy switch` mints a **deployment record** on the same graph carrying both the commit and the config version, and that the dry-run boot validates that exact pair.

### M8 — Hot-room retention has no variable and replay has no read path after purge.
TN-3's sync runs "verify-before-purge", but the purge horizon is not among the ~40 minted variables, and TN-21 reads recorded observations "from the **live world room**" — which, past the horizon, no longer holds them. **Fix:** mint `hot_room_retention_window` as a `configurable: true` node variable, and state that a replay whose range predates it reads the evidence tier through the same one-way replay import port (H7).

### M9 — `max_slice_latency` is declared with no consequence.
TN-5 declares "a declared maximum slice latency (node value)" and A6 records it as an assumption; nothing says what happens on breach — refuse, alarm, shed, or stand down. TN-15 exports slice latency as a process metric only. **Fix:** state the consequence (a typed refusal plus a `data quality` record plus a `no-new-entry` effect, entry-side per L39) or demote it to a watched target with no gate, as TN-23 does for the 50 ms rung.

### M10 — The accumulator's ordering authority and TN-4's drain-order discipline are two orderings of one stream.
TN-4: "execution and system events are served **before** market data". TN-5: "recording precedes interpretation … folded into the **next** slice", and AD-37 gives one arbitration point per stream. Reordering at the accumulator changes the slice sequence the loop's identity-bearing sub-phase order operates on. **Fix:** state that drain-order priority applies to **dequeue for interpretation** and never to the record-and-journal order, so the recorded stream preserves arrival order and the replay diff stays meaningful.

---

## LOW

### L1 — The Linux CI lane can never be the benchmark regression gate.
TN-23 records baselines "on the VPS's declared `(OS, CPU-class)` tuple" and calls the first baseline "the regression gate"; TN-16's CI lane runs on a GitHub `ubuntu-24.04` runner with a different CPU class, so it cannot evaluate that gate. Worth one sentence saying the benchmark gate runs on the VPS at the soak and in the nightly window, and CI runs the harness for correctness only.

### L2 — `qmn` / `qmx` naming blast radius under Q1.
`qmn` is A1/Q1-pending, but `/opt/qmx` (TN-16), the `qmx/*` credential labels (TN-3, TN-12) and `qmn_`-prefixed metric names (TN-15) mix the two names. Worth a sentence naming which identifiers move if Q1 answers differently, so the epics do not hardcode.

### L3 — Per-stream metrics need an opaque-id mapping with a declared home.
TN-15 says labels "never carry secrets or account numbers beyond **opaque ids**" while exporting per-stream and per-connection families keyed by `(VenueId, account)`. The opaque-id ↔ account mapping table has no declared owner or home; it belongs with the roster in the config artifact.

### L4 — The structural seed omits the `qa/` tree.
TN-23 requires "requirements-first independent tests in the **`qa/` tree**" and the Capability map lists `tests/`, `qa/`; the Structural Seed shows only `tests/` and `examples/`. One-line addition.

---

## What I could not fault

- The four-verdict reconciliation correction and its propagation through TN-10, TN-7 and the vocabulary mint — internally consistent everywhere it appears.
- The veto and suppression paths as named first-class outputs of the order path, with `enacts` edges. This is the single best structural idea in the spine and it is drawn correctly in the TN-6 diagram.
- The refusal to mint a fourth control-window kind for venue maintenance (TN-11), reasoned from the sensing-outage rule rather than by assertion.
- "An alert is evidence, not permission" and the records-versus-delivery two-plane rule (TN-15).
- RTO measured at the first rehearsal, never declared (TN-13); the operator's ~50 ms recorded as a watched target, never a budget (TN-23). Both correctly apply AD-13 against the pull to state a number.
- The L30 reconciliation note handed to the documentation factory to annotate **at source** rather than a child spine settling a parent invariant silently (TN-1, Dependency direction). Exactly the right move.
- The A1-A30 register and the four operator questions. Every without-operator call is individually overturnable and cited from the rule that depends on it; this is what makes the spine safe to act on despite the findings above.

## Gate recommendation

**CONDITIONAL PASS.** C1-C7 must be closed before the spine is handed to `bmad-create-epics-and-stories`, because each one is a hole that *epic boundaries themselves* will fall into — every one of them was constructed as a pair of plausible epics, and four of them (C1, C2, C3, C4) can move or trap real money at the soak. All seven are closable by adding or tightening a sentence in an existing TN; none requires a new TN, a new decision from the operator, or re-litigating anything the adjudicators settled. H1-H15 should be closed in the same pass — they are the same class of defect at lower blast radius, and they are cheapest to close now, while the rules are still one document rather than twenty-three epics. Medium and low findings can ride into the documentation-factory increment.
