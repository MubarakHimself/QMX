# Reviewer gate — LENS: parent / sibling consistency

**Subject:** `architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md` (TN-1..TN-24) + `.memlog.md` (37 entries, A1-A30)
**Against:** QMF parent spine AD-1..AD-41 (`architecture-QMX-2026-08-19`), QMB B-1..B-15 (`architecture-QMB-2026-08-20`), QML QL-1..QL-10 (`architecture-QML-2026-08-21`), `docs/constitution.md` L1-L39 (incl. L30's 2026-08-21 roster-scope annotation), and the ratified `DEPENDENCIES.md` register on `integration@ef9bb25`.
**Question this lens answers:** for every TN, does it weaken, contradict, re-derive, or silently amend an inherited AD / B / QL / L?
**Date:** 2026-08-28. Reviewer: parent-consistency seat.

**Verdict: FAIL-with-amendments.** The spine is unusually faithful in shape — the inherited-invariant table, the four adjudicated corrections, the KSA adoption note and the L30 reconciliation note are all done the right way (surfaced, not overridden). But four inherited invariants are contradicted outright, and eleven more are narrowed, re-derived, or left without a home. Three of the four criticals would ship as code the epics cannot walk back cheaply (automated de-escalation, a silently-reset ledger, a duplicated connection manager). None require re-opening a ruling; all are amendments at the spine desk.

**What this lens found GOOD, so the amendment pass does not undo it:**

- TN-1's L30 note is stated correctly as a conflict-to-surface: *"the doc factory annotates L30 at source"* / *"rather than a child settling it silently"* — the same discipline QL-1 used, and the right one.
- TN-5 preserves B-2's six sub-phases verbatim, keeps "new intents rest a slice", keeps declared instrument order and the forming-bar prohibition.
- TN-10 carries AD-27's four verdicts, the gates-the-command-pipe-only rule, and AD-36's re-decide-not-retry.
- TN-11's error-map default, two-artifact capability surface, `converted_by = venue` equity provenance and no-command-retry rule are AD-28 verbatim.
- TN-24 (a) and (b) correctly override adjudicator B against the parent text (AD-40 partial-fill re-base; AD-27 venue-native dedup key).
- TN-19 is faithful to QL-4/QL-7/QL-8/QL-10 including the four pinned prediction-linter checks and the host-owns-only-process-spawn split.
- Banned vocabulary is clean: zero uses of engine / kernel / plugins / exam / minimal core outside the convention row; zero "timeframe"; zero bare "stop-out"; `suspend_new` spelled one way throughout; "the trading node" with modes `paper | live` held everywhere — no "paper node".

---

## CRITICAL

### C-1 — TN-7 makes `drain` auto-satisfiable; AD-36 pins it `never-auto`

**Where:** TN-7, "Under a dead wire or an outstanding UNKNOWN" bullet.

**Parent sentence (AD-36):** *"Each action kind declares a mandatory satisfaction predicate from a closed vocabulary — `scope-flat-at-reconciled-verdict | no-pending-orders-at-reconciled-verdict | never-auto` — and **`suspend_new` and `drain` are `never-auto` by rule**, clearing only by an operator `resume`, which is what keeps automated de-escalation forbidden rather than reachable through the satisfaction clause."*

**Spine sentence (TN-7):** *"`drain` and `close_all` become STANDING PROTECTION INTENTS — journaled before dispatch, restart-proof, re-decided never retried, never time-expiring, **satisfied only on a `reconciled` verdict**, alarming and holding open on `drift | unknown | out-of-lookback`."*

**What:** the node collapses two different satisfaction predicates into one. AD-36 gives `flatten` the reconciled-verdict predicate and gives `drain` `never-auto`. TN-7 hands `drain` the reconciled-verdict predicate.

**Why it matters:** this is exactly the hole AD-36 wrote that clause to close. A node that clears a `drain` on a reconciled verdict has de-escalated a protection state automatically — the one thing "escalation automates; de-escalation does not" and "`resume` is operator-only" forbid. It would pass every test the spine describes and silently resume new entries after a connectivity event.

**Fix:** in TN-7, split the sentence: *"`close_all` becomes a standing protection intent satisfied only on a `reconciled` verdict showing the scope flat; `drain` and `suspend_new` are `never-auto` — they stand until an operator `resume`, a reconciled verdict never clears them."* Add "satisfaction predicate" as a mandatory declared cell of `ksa_effect_matrix` alongside effect and typed scope (AD-36 requires it per action kind).

### C-2 — `state_carry`, `carries-ledger` and `continues-performance` appear nowhere in the spine

**Where:** absent from TN-9 (paper flip), TN-18 (settings edit → new config version), TN-20 (operator-signed acts), TN-22 (roster). Grep-verified: zero occurrences of `state_carry`, `carries-ledger`, `continues-performance` in the whole node spine.

**Parent sentences (AD-29):** *"Any change to any tuple component mints a new binding, and what carries is declared, never inferred. Every binding record carries a mandatory, non-defaultable **`state_carry`** declaration — per counter (`ledger`, `cycle`, `budget`, `bench_counter`, `exposure`), each `carry | reset`; **absent is an `invalid input` refusal**. `carry` is legal only where a human-signed **`carries-ledger`** edge accompanies it."* AD-41 adds: *"[the bench fold's] stream boundary is the binding epoch: a new epoch starts the count at zero unless a signed `carries-ledger` edge spans it."* AD-30: *"A changed number changes `fp1` ⇒ a new Book identity ⇒ a new binding ⇒ **a fresh cycle's money**, unless the new binding's `state_carry` declares carry…"*

**Spine sentences:** TN-9 — *"paper is a Book-level mode … expressed as a dated binding-epoch change."* TN-18 — *"an edit through the CLI or the powers channel mints a new config version … a change takes effect at the next boot epoch."* TN-17 — *"settings edit, which mints a new config version and schedules a restart at a safe point."*

**What:** the node mints new binding epochs in at least four places (paper flip, kill-line stand-down return, any Book/BMS number edit through the powers door, a BMS re-version) and never declares what carries across them.

**Why it matters:** an unbuilt `state_carry` is not a missing nicety — AD-29 makes its absence a refusal, and its default is silence in both directions. Without it, the operator edits a dead-zone width through the settings surface, the node restarts, and either (a) the virtual ledger, budget remainder and bench counters silently reset to zero — a fresh cycle's money nobody signed for — or (b) they silently carry — money moved with no `carries-ledger` signature. Both are money-path failures that no test in TN-23 would catch.

**Fix:** add to TN-18: every config version whose diff touches a Book- or BMS-identity-bearing field mints a new AD-29 binding, and the powers-door edit flow must collect a `state_carry` declaration per counter plus a human-signed `carries-ledger` edge for any `carry`, refusing (`invalid input`) if absent. Add to TN-20: `carries-ledger` and `continues-performance` are two more operator-signed acts, never inferred from one another. Add `state_carry` to TN-22's roster shape and to TN-9's paper flip.

### C-3 — TN-11 relocates the cTrader transport and the connection manager into `qmn`; qmf-venue already owns both

**Where:** TN-11 rule; adjudicated Correction 4; Structural Seed (`src/qmn/venue/ctrader/  # transport, codec, connection manager, duties, verification suite, equity`); Stack row.

**Parent / register sentences:**
- `DEPENDENCIES.md:47` — *"**qmf-venue owns its own transport**: the Spotware `openapi-proto-messages` release (integer tag 91) is compiled **in-house** … Declared only in `packages/qmf-venue/pyproject.toml`"*, and the register's prose: *"the protobuf runtime is a **qmf-venue-only** dependency — no other package declares or imports it."*
- AD-28 — *"The adapter's connection manager is the **sole owner of venue sessions** … **no other component may construct a venue client**."*
- AD-26 — *"**The connection manager is the single named component permitted to hold secret values in memory**."*
- Parent Structural Seed — *"`qmf-venue/  # module: AD-26/27/28 neutral port (CT-18..21); cTrader adapter #1`"*.
- Ground truth on `integration@ef9bb25`: `packages/qmf-venue/src/qmf/venue/connection.py:361` already defines `class ConnectionManager` ("the sole owner of venue sessions and the single in-memory holder of secret values"), and `proto.py` already carries the in-house tag-91 compilation ("`COMP-QMF-VENUE` owns its own transport").

**Spine sentences:** *"the node ships the IN-HOUSE transport `qmf-venue` deliberately lacks: an asyncio TLS socket … length-prefixed `ProtoMessage` framing over the pinned proto release tag 91 compiled in-house against `protobuf==7.36.0` … request encoding; `clientMsgId` generation and matching; the submit path; market-data subscription; account auth; and in-band token refresh … **All of it lives inside the connection manager**"* — and Correction 4: *"`qmf-venue` compiles proto tag 91 in-house … **the node owns its transport**."*

**What:** three contradictions in one decision. (i) One sentence says qmf-venue compiles the proto and the node owns the transport. (ii) The node's own Stack table says *"protobuf (qmf-venue only) | ==7.36.0"* while TN-11 requires `qmn` to do `ProtoMessage` framing and request encoding — which cannot be done without importing the compiled messages, i.e. protobuf becomes a node dependency the register says no other package declares. (iii) The Structural Seed puts a second `connection manager` in `qmn`, beside the one qmf-venue already ships — the exact "second cTrader client" TN-6 lists under **Prevents**, and a second in-memory secret holder against AD-26.

**Why it matters:** this is the largest single block of node work (the parts-bin's does-not-exist cluster 3) and the epics will be written against whichever locus the spine names. Getting it wrong means either a duplicated ConnectionManager with two secret-holding paths, or a late re-home of the whole transport.

**Fix:** decide and declare the locus. Recommended: the asyncio TLS socket, framing, encoder, subscription and submit path are a **qmf-venue increment** (they complete the existing `ConnectionManager` and stay inside the one component AD-26/AD-28 name), delivered as QMF-side stories that the node's epics depend on; `qmn/venue/ctrader/` then holds only what is genuinely node-side — duty scheduling, the verification-suite runner, equity derivation, the CT-18 field fills and the error-map rows. If instead the operator wants it in `qmn`, that is an amendment to AD-28, AD-26 and `DEPENDENCIES.md:47` and must be surfaced for the doc factory exactly as L30 was, not asserted in a child.

### C-4 — TN-21's replay reads the live world room while asserting cross-world reads refuse

**Where:** TN-21 rule, first and third bullets.

**Parent sentences:** AD-19 — *"seven room-roles … **instantiated per world** (AD-12): **a read that crosses worlds is a `policy rejection` refusal**."* AD-12 — *"a non-live world may never write into the live evidence namespace … Identity distinctness alone does not deliver world separation — storage separation does."* AD-29 — *"a replay of a binding mints a different binding identity, and AD-19 refuses cross-world reads, so replay-derived and live evidence are **deliberately incomparable by binding**."*

**Spine sentences:** *"a REPLAY VENUE ADAPTER behind the same neutral port, **feeding the recorded observations (ticks, bars, fills, lifecycle events) from the live world room**"* … *"Every artifact is `world = replay` … replay never writes into live rooms; **a cross-world read is a policy rejection**."*

**What:** the mechanism the rule describes is the refusal the same rule states. A `world = replay` run reading the live world room is a cross-world read.

**Why it matters:** TN-21 is a required step of the soak acceptance and of every order-path change (TN-23). As written it either cannot run at all, or it runs by an undeclared exemption that quietly punctures the storage separation AD-12 says is the only thing delivering world separation.

**Fix:** name the crossing. Either (a) declare replay's input as an explicit, fingerprinted **export** from the live raw archive into the replay world's rooms (a copy with lineage, satisfying "storage separation"), or (b) propose a third declared read exception to AD-12 — alongside AD-35's decay-cohort read and AD-31's entity projection — as a parent annotation for the documentation factory, with `world` carried on every row and no write exception ever. Option (a) needs no parent amendment and is the cheaper build.

---

## HIGH

### H-1 — "virtual (Book) position" vs "venue position" is nowhere in the spine

**Where:** TN-8 (kill-line flatten), TN-10 (explained drift), TN-11 (equity derivation), TN-24 (a)(d)(f). Grep-verified: the word "virtual" occurs once, in TN-10's "broker-versus-virtual divergence"; "virtual position" never occurs; the Consistency Conventions table omits the pair.

**Parent sentences:** parent Consistency Conventions require *"**virtual (Book) position** vs **venue position**"* be named apart. AD-40 — *"A **venue position** is observation-derived … A **virtual (Book) position** is a fold over fills joined by declared command identity: binding-scoped, Bot-attributed … **Every risk record names which of the two it references.** Where CT-18 declares `netting`, the fill-to-virtual-position attribution rule is a **mandatory Book declaration** whose absence is a bind-time `policy rejection`."* AD-41 — *"The exit record (CT-29), one per **virtual** position close … or a netted account produces fewer records than admissions and every fold over them under-counts."*

**Spine sentences:** TN-11 — *"EQUITY DERIVATION — balance plus per-position unrealized P&L"*; TN-10 — *"open unrealized P&L **on positions**"*; TN-8 — *"A breach auto-flattens that binding's scope"*; TN-24(d) — *"**Position mismatch** on restart."*

**What:** every one of those "positions" is ambiguous, and on a netting account the two readings are different numbers. The bench fold, CT-29 record count, drift decomposition and kill-line scope all hang on the distinction.

**Why it matters:** cTrader accounts declare `netting | hedging` per account (CT-18). If the node's equity, drift and flatten paths are built against venue positions while CT-29/AD-41 folds want virtual ones, the bench under-counts and the kill line flattens another Book's exposure.

**Fix:** add the pair to TN-24's Consistency Conventions row; qualify every occurrence in TN-8/TN-10/TN-11/TN-24; and state in TN-10 that the sum of virtual positions reconciles against the venue's netted position through AD-27 reconciliation evidence (AD-40's own words).

### H-2 — TN-22/TN-5 omit AD-29's netting-vs-hedging bind-time check and the shared-flatten signature

**Where:** TN-5 (*"Several Books on one account share it"*), TN-22 (roster, one BMS per account). Grep-verified: `hedging` never appears; `netting` appears once, only as "cross-account netting, NOT built now".

**Parent sentence (AD-29):** *"**On a `netting` account they also share positions** … a Book-scoped flatten mechanically closes another Book's exposure … Binding a second Book onto a netted account whose live bindings may trade an overlapping instrument set is an `unsupported capability` refusal **unless the operator signs the shared-flatten limitation**, that signature being an identity field of the binding. **The recommended default configuration is one Book per netted account.**"* Plus AD-36/AD-37: *"where the venue's position model makes a narrower scope indistinguishable from a wider one (netting) the action **refuses**."*

**What:** the node sanctions several Books per account without importing the refusal, the signature, or the recommended default.

**Fix:** add to TN-22: the position model is read from CT-18 at bind time; a second Book on a netted account with an overlapping instrument set refuses unless the operator signs the shared-flatten limitation (identity field of the binding); the V1 default is one Book per netted account. Add to TN-6: a scope the position model makes indistinguishable from a wider one refuses rather than executing wider.

### H-3 — TN-8's `amend_min_improvement` withholds a risk-reducing act (L39 / AD-36)

**Where:** TN-8, node-minted variables: *"`amend_min_improvement` per Book, the tick-storm amendment-suppression threshold (PRD row 12d), where a skipped amend is journaled."*

**Parent sentence (AD-36 / L39):** *"No control action, of any authority, at any scope, may block a **risk-reducing** act: `cancel_order`, `close_position`, `close_all`, **a risk-non-increasing `amend_protection`**, a protection action, or the recording of evidence."*

**What:** a threshold that suppresses an `amend_protection` because the improvement is small is a block on a risk-reducing act, journaled or not. The node lists L39 as binding on TN-8 in the same block.

**Why it matters:** the exception is small and reasonable-sounding, which is exactly how the invariant erodes. It also creates the first precedent for "a control that withholds, but only a little".

**Fix:** re-site it as **origination policy, not a gate**: the breakeven ratchet's own trigger hysteresis inside the Book's `exit_policy` — the Book declares when it *proposes* an amendment; nothing on the command path ever refuses one that was proposed. Rename accordingly (`breakeven_ratchet_min_step`), and state in TN-8 that no node component may refuse a risk-non-increasing `amend_protection`.

### H-4 — TN-24(f) "only the kill line flattens" contradicts AD-36, AD-33 and TN-8 itself

**Where:** TN-24(f).

**Spine sentence:** *"**Money boundaries** — rollover, sweep, re-seed, paper flip — never touch positions; **only the kill line flattens**."*

**Parent sentences:** AD-36 assigns flatten authority to *"(1) The operator — always, at any scope … (2) Book policy, only through pre-declared trigger classes — a kill-line breach … (3) The protection authority (kill-switch class), where the node's severity policy declares `close_all` for that severity."* AD-33's close-reason taxonomy carries `hold_time_force_flat | boundary_flat | window_forced_flat | protection_forced_flat | operator_close` — five other flattens. AD-37 ranks *"BMS/Book forced flats (kill-line stand-down, window force-flat, hold-time or boundary force-flat)"* at rank 2.

**What:** the clause as written deletes four ratified flatten paths, and contradicts TN-8's own matrix, which lets the protection authority carry a flatten effect.

**Fix:** rewrite as the parent states it: *"a money-accounting boundary is never itself a flatten trigger; flatten authority is AD-36's three (operator; Book policy through pre-declared trigger classes, kill-line breach included; the protection authority per the matrix) and never the adapter. A declared window force-flat that coincides with a boundary is a separate declared trigger and is honoured."*

### H-5 — TN-7 mis-cites CT-30's vocabulary (`close_all` for `flatten`)

**Where:** TN-7, the matrix bullet: *"effects drawn ONLY from CT-30's vocabulary — `suspend_new | drain | close_all` with a required typed scope."*

**Parent sentence (AD-36):** CT-30's kinds are *"`suspend_new` … **`drain`** … `flatten` (close the scope), `resume`."* `close_all` is a CT-19 **command** kind (AD-27's five) and a CT-18 **protection primitive** (AD-28's roster) — three different rosters, and the node has picked from the wrong one while naming CT-30.

**Why it matters:** `ksa_effect_matrix` is a registry variable set whose cell values are this vocabulary. A matrix built on `close_all` cannot be resolved through CT-30's pinned scope-resolution table, and the CT-30→CT-29 close-reason mapping (*"every (CT-30 action kind × issuing authority) maps to exactly one close reason"*) has no row for it.

**Fix:** effects are `suspend_new | drain | flatten`, each with a required typed scope; note in one clause that a `flatten` resolves at dispatch into `close_position` / `close_all` CT-19 commands per CT-30's resolution table. The memlog's own TN-7 entry wrote "flatten/close_all" — the spine dropped the correct half.

### H-6 — TN-6's protection gate carries no entries-only qualifier

**Where:** TN-6 chain and the order-path diagram: `MINT → GATE[protection gate — KSA fold, standing-intent fold, UNKNOWN block] → CM`.

**Parent sentence (AD-36 / L39):** *"The **blocking** half of any control is always **entries only** — in paper and live alike; a control may additionally **act** (`drain`, `flatten`), but it may never **withhold** a risk-reducing act."*

**What:** the diagram shows one linear chain for all five command kinds; exits, `cancel_order`, `close_position` and `amend_protection` traverse the same gate, and the gate is described as blocking. Nothing in TN-6 says the KSA fold blocks entries only.

**Why it matters:** a builder reading TN-6 alone wires a gate that can trap a position behind a kill-switch level — the precise failure L39 exists to prevent, and the one AD-36 calls out by name.

**Fix:** state in TN-6 that the protection gate's blocking half is entries only; risk-reducing commands pass it unconditionally and are dispatched ahead of `place_order`. Show the exit lane bypassing GATE's block in the diagram. Add the one legitimate exception explicitly: AD-27's per-command `UNKNOWN` block, which does hold protection commands, but under which *"a protection act the block refuses never evaporates: it stands as an AD-36 protection intent"* — and extend that standing-intent coverage per H-7.

### H-7 — Standing-intent coverage narrowed from "every risk-non-increasing act" to two CT-30 kinds

**Where:** TN-7 (only `drain` and `close_all` become standing intents); nothing in TN-6, TN-8 or TN-24(g) extends it.

**Parent sentence (AD-36):** *"**The standing-intent machinery binds every risk-non-increasing act, not only CT-30 kinds** — naming `amend_protection` (AD-34) and CT-23's `close_full` / `tighten_protective_stop` (AD-33) and every protective close. Journaled before dispatch, resolved as a read-time fold, re-decided rather than retried, never time-expiring, alarming when undeliverable. Without this the apparatus would cover the four control kinds and leave most actual protective acts to evaporate on the first transient refusal."*

**Fix:** in TN-6 (protection gate) and TN-8 (ratchet), state that a refused `amend_protection`, `close_full` or `tighten_protective_stop` stands as a protection intent under the same machinery, journaled before dispatch, re-decided at the next reconciled verdict. Add a soak-gate item in TN-23: a protective amend refused under an outstanding UNKNOWN is re-decided, not lost.

### H-8 — TN-11 pins "five verify-or-refuse checks"; amend atomicity has no home

**Where:** TN-10 step 2, TN-11, TN-23 ("five first-connection checks passed per instrument").

**Parent sentences:** AD-28 — *"an unverified spot-timestamp unit refuses spot evidence; an unmeasured daily boundary …; a failed bar-basis reconciliation …; a failed pip-formula validation …; an absent money exponent …; **an unverified amend-atomicity verdict refuses any Book policy that depends on amending both protection sides in one act (AD-34), leaving single-sided amendment as the only legal path**."* AD-34 — *"**Amend atomicity is UNDOCUMENTED in every primary source** … a `measured-at-connection` CT-18 field under AD-28's verify-or-refuse posture."*

**What:** TN-8 states the consequence ("single-sided until amend atomicity is measured at the venue") but no TN gives the measurement a place in the boot ceremony, the verification suite or the acceptance gate — so it is never measured, and the consequence is permanent by omission rather than by rule.

**Fix:** either widen the suite to six named checks (adding amend atomicity, journaled `data quality` into the venue-observation profile) or state explicitly in TN-11 that amend atomicity is measured by a separate declared drill and remains unverified in V1, with single-sided amendment permanent for the phase. Whichever is chosen, add it to TN-23's checklist.

### H-9 — TN-21's "same neutral port" binds a seam the node's own ports table says does not exist

**Where:** TN-21 (*"a REPLAY VENUE ADAPTER behind the same neutral port"*) vs the Ports table row for `ProbeTransport`: *"The ONLY Protocol in `qmf-venue`: **there is no `VenuePort`/`OrderPort`/`VenueAdapter` seam**, so the live client is composed AROUND the concrete typed values, never injected into them."*

**Parent sentences:** AD-28 — *"**One neutral port, four contracts** … per-venue adapters implement them … A CCXT-class crypto venue slots in later by declaring a different record **through the same port**."* L22 — *"The Venue module must preserve a venue-neutral seam so later crypto and stock adapters do not change foundational contracts."* B-2 — *"Backtest/replay/live differ only by which clock and **adapters** the run-config binds."*

**What:** the node records, as ground truth, that the parent's central venue abstraction is not implemented — and then designs two mechanisms (TN-21's replay adapter, TN-5's "differ only in which clock and adapters the root binds") that require it. It is recorded as an inventory fact in a table, never surfaced as an inherited-invariant conflict.

**Fix:** promote it to a declared conflict-to-surface, exactly as L30 was: either the node mints the missing seam as part of its work (a `VenuePort` over CT-19/CT-20 that both the cTrader client and the replay adapter implement — the cheapest way to make TN-21 and TN-5 true), or the spine states that AD-28's "one neutral port" is an unimplemented parent claim and TN-21's replay substitutes at the accumulator boundary instead. Do not leave both readings live.

### H-10 — AD-31's risk-domain writer unit and the risk dispatcher's block-on-unpersistable duty are missing

**Where:** TN-3 (WriterIds for the service, calendar, backup, restore drill), TN-19 (Bot-domain WriterId), TN-22 (per-stream WriterId). No TN names a writer for `decision`, `risk transition`, `control action` or `promotion` events.

**Parent sentence (AD-31):** *"**The risk-domain writer unit is `(machine, risk role, binding)`** — declared here because AD-21's gapless per-(writer, boot-epoch) sequence otherwise has no owner for `decision`, `risk transition`, `control action` and `promotion` events, and gap detection cannot work without one. **The block-on-unpersistable obligation binds the risk dispatcher exactly as AD-28 binds the connection manager:** a control action is journaled *before* dispatch, so the dispatcher must see a sink refusal — a `storage failure` blocks the dispatch rather than losing the intent."*

**Why it matters:** the veto path (TN-6), every CT-30 control action (TN-7/TN-8) and every promotion (TN-20) write into streams with no declared writer, so TN-2's boot-epoch stamping and TN-15's sequence-gap metric have nothing to attach to; and the "journaled before dispatch" guarantee has no component obliged to see the refusal.

**Fix:** add the risk-domain writer `(machine, risk role, binding)` to TN-2's compose step and TN-3's WriterId inventory, and state the risk dispatcher's block-on-unpersistable duty in TN-6 beside the connection manager's.

### H-11 — No declared slice-frontier instant, so TN-21's decision diff can differ for non-decision reasons

**Where:** TN-5 (*"a live frontier clock (the real wall clock injected as qmf-core's `Clock`)"* + *"Slices are event-driven per observation"*) vs TN-21 (*"the replay frontier clock — a pure function of the data cursor"* + *"the produced decision stream is DIFFED against the recorded one"*).

**Parent sentence (B-2):** the frontier clock is *"monotonically non-decreasing, pulled to the minimum next-emit instant across streams"*; AD-8 keeps foreign timestamps as evidence with a mandatory local receive wall stamp, and *"instants alone never totally order events"*.

**What:** live slices are cut by observation arrival against a wall clock; replay slices are cut by the data cursor over recorded instants. The spine never says which instant is the slice's frontier — the venue event instant or the local receive instant — so two out-of-order arrivals that produced one live ordering can produce another under replay, and the diff reports a decision change that is not one.

**Why it matters:** TN-21 is the regression gate for every order-path change and a soak-acceptance item. A diff that is not stable is not a gate.

**Fix:** declare in TN-5 that the slice frontier is the **receive wall instant** stamped by the accumulator (with the venue instant carried as evidence), that the accumulator's recorded stream order is the replay cursor order, and that a replay reproduces slice boundaries from the recorded receive stamps — making the diff a decision diff and nothing else. State that a live frontier is monotonically non-decreasing by construction because the accumulator stamps, not the venue.

---

## MEDIUM

1. **`kill_line_capital_floor` is a second name for `loss_floor`.** AD-40: *"`loss_floor` is the same number the kill line names — **one value, one name**, declared once and read by both, never two floors that can drift apart."* TN-8 mints `kill_line_capital_floor` "the SAME number as AD-40's `loss_floor`". Fix: use `loss_floor` and record `kill_line_capital_floor` as a display alias only, or drop it.
2. **`decision_freshness_bound` is absent.** AD-39 makes it a *"mandatory, non-defaultable"* Book variable and refuses at the door any SQS configuration whose max input age exceeds it. TN-8's seven `sqs_*` keys omit it, and TN-18's do-not-default list does not carry it. Fix: add it to the variable roster (Book scope) and to TN-18's blank-blocks-live set.
3. **`instrument_class` record kind is absent.** AD-39: *"Instrument class is a dated AD-9 instrument-metadata record kind (`instrument_class`) … no class record ⇒ blocked, absence journaled as `data quality`."* TN-8 says "hard-block threshold per class" and TN-13 mints the parallel currency-exposure records for news but never the class records for SQS. Fix: name `instrument_class` alongside the currency-exposure record in TN-8/TN-13 with the same fail-closed rule.
4. **Dead-zone "posture" is a default by another name.** AD-38: widths *"are configurable UI-editable variables with no spine value. Recorded evidence, non-authoritative and **never a default**."* TN-8: *"this sitting's posture is the wider band around the daily rollover, fail-closed."* Fix: state the fail-closed blank rule only, and move the wider-band preference to an operator recommendation in the hand-off, not the spine.
5. **TN-14's "no local time is ever stored, keyed or compared" forecloses a parent-permitted mechanism.** AD-8: *"A **civil-time bucket key** … is a legitimate computed value (seasonality, session-of-day statistics) … 'Local time is display-only' governs evidence timestamps, not computed grouping keys."* AD-39's SQS baseline is conditioned on a named session window — exactly such a key. Fix: qualify to "no local time is ever stored as an evidence timestamp, key or comparison; AD-8's civil-time bucket keys remain legal and identity-bearing including zone and tzdata version."
6. **Paper roles collapsed onto `demo`.** AD-9 roles are live / demo / paper-validation / paper-benched / prop-firm; AD-12 role-scopes the namespaces accordingly. TN-9 declares one paired account with role `demo` for both the Book-mode PAPER flip and (via AD-41) benched-seat routing, so two different evidence classes land in one namespace. Fix: state which role each routing reason writes under, or declare the collapse deliberately with the consequence stated.
7. **Cross-role reads not declared for the door's projections.** AD-31: an entity projection over an entity that operated in more than one role *"is a declared cross-role read, permitted, with `role` carried on every row and never aggregated across roles without an explicit declaration."* TN-17's evidence channel serves "journal projections (Book, BMS and per-bot logbooks)" with no such declaration. Fix: declare it in TN-17 and require `role` on every projected row.
8. **`composition_fp` omits extension distribution identity + version.** AD-2: an extension's *"distribution identity + version are identity fields of every artifact it produces"*; a tzdata pin change is at minimum a minor bump. TN-2 lists qmf/qmb/qml/qmn, proto tag, tzdata version and the OS/CPU tuple, but not the registered calendar/indicator/structure extensions it composed. Fix: add them to the fingerprint recipe.
9. **Treasury boundary-event kind not named.** AD-16 reserves a treasury boundary-event record (`sweep | refund | re_seed | paper_epoch_reset`) mapped onto AD-21's `risk transition`, and *"no money moves without one"*. TN-10's missed-rollover catch-up says only *"the sweep journaled as a correction-style append."* Fix: name the record kind in TN-10 and TN-9 (`paper_epoch` already close).
10. **The MIS signal snapshot sits on the trading path with no AD-24 declaration.** TN-19: *"computed in-process by rule-based deterministic labelers and dispatched SYNCHRONOUSLY … to the Book door and the KSA."* AD-24: a configuration is light only if it declares **and benchmark-proves** four bounds, and *"a heavy configuration's synchronous entry point returns `unsupported capability`"*. Fix: state that every V1 labeler is declared light with the four bounds and is benchmark-policed on the deployment tuple, or that the snapshot is fanned out with a staleness stamp and consumed under a declared maximum age.
11. **AD-24's heavy-by-default bootstrap is unsequenced against the soak.** *"Until the live-path rung has a recorded baseline, every configuration is heavy by default and a light claim is refused at the gate."* TN-23 records that baseline **during** the soak, while TN-9 says the soak runs the full door machinery. Fix: sequence it — record the rung baseline in the first hours (a boot-time benchmark pass), then open the doors; or state which doors run degraded until it exists.
12. **AD-19's seven room-roles are never mapped, and the replay world has no rooms.** TN-3 names a hot tree (raw archive, journal, live world room) and an evidence tier. AD-19 instantiates seven room-roles **per world** — including the registry room and the split-governed research door — and TN-21 produces `world = replay` artifacts with no located home. Fix: add a room-role → placement table to TN-3 covering both worlds.
13. **No `corroborates` / `disagrees-with` posture for the two tick sources.** AD-21: *"Tick sources are separately identified (Dukascopy history vs broker feed) … disagreements between sources stay visible via `corroborates` / `disagrees-with` edges, never merged."* TN-13 creates exactly this overlap (the venue-history continuity bridge against the Dukascopy archive) and TN-11 makes tick-based backtest-to-live comparison the interim rule. Fix: state the edge posture in TN-13.
14. **"Every arbitration loser is suppressed" is over-broad.** AD-37: *"Actions whose effects **compose** (`suspend_new` + `flatten`, `drain` + `flatten`) **both execute**; only mutually exclusive actions arbitrate,"* plus the standing invariant that a higher rank may never reduce the protection a lower rank would have delivered. TN-6 states the suppression rule flatly and the diagram routes every loser to the suppression path. Fix: import the collapse rule, the compose rule and the standing invariant into TN-6.
15. **Fold contracts not declared per fold.** AD-36 requires each fold to declare stream, ordering key, knowledge-time bound and equal-instant disposition, and to resolve across writers *"by AD-37 rank — never by `WriterId` byte order"*. TN-7 names the stream for the KSA fold; TN-10 lists seven folds with none of the four declarations; the rank-not-WriterId rule is nowhere. Fix: add a fold-contract table (fold → stream, ordering key, knowledge-time bound, equal-instant disposition) to TN-10.
16. **AD-18's plain-words summary is missing from the promotion flow.** AD-18: *"a mandatory plain-words summary field that is **explicitly declared an identity field** — the signature attests the exact words the human read."* TN-20 carries the card `fp1` + `correlation_id` rule correctly but never requires the powers door to render and store the summary. Fix: name it in TN-20 and in TN-17's powers channel.
17. **TN-24(e) turns AD-41's configurable default into a rule.** AD-41: *"`q` is a declared, UI-editable, per-family template variable defaulting to approximately one R … **Scratches and partial losses do not count by default**. **Breakevens never count under any `q`**."* TN-24(e) says breakeven and scratch count for neither, flatly — hardening a per-family configurable into spine law for scratches (breakevens are correct). Fix: "breakevens never count under any `q`; scratches count only where the Book's declared `q` reaches them."
18. **One word, two states: node "stand-down" vs binding `stood-down`.** AD-36/AD-41 enumerate the binding state `stood-down` and warn *"a state word that appears in neither list does not exist."* TN-4 mints a node lifecycle "stand-down", the Conventions row defines only that one, and TN-8 says a kill-line breach *"stands the **Book** down"* — writing a binding state onto a Book (AD-41: *"a seat-state write never writes a Book-mode row"*). Fix: name them apart in the Conventions row (node stand-down vs binding `stood-down`) and correct TN-8 to "stands that **binding** down".
19. **B-3's derived-fragment discipline not restated.** B-3: Book/BMS fragments are *"generated, schema-validated, fingerprinted DERIVED artifacts carrying AD-16 lineage edges back to their source Book/BMS definitions … never free-hand-edited."* TN-18 lists them as precedence layers without that property, and TN-17's "settings edit" could be read as editing a fragment directly. Fix: state that the node's BMS/Book fragments are derived-with-lineage and that an edit mints a new source definition version, never a fragment edit.
20. **Category error in TN-6's do-not-default roster.** *"The node OWNS these, do-not-default, UI-editable, and blank blocks `role = live` bindings: … the **evaluation of the sizing ladder** … and the **issuance of `resolve_unknown`**."* Neither is a value that can be blank or UI-editable; TN-18's own do-not-default list correctly excludes them. Fix: split the list into "values the node owns (do-not-default, UI-editable, blank blocks live)" and "responsibilities the node owns".
21. **The sealed period's one logged final look has no door.** AD-21: *"the sealed period gets one logged final look, journaled as a named `control action` subtype, and is never silently recycled."* TN-13 enforces the seal at every read but the node's doors offer no sanctioned final-look path, so the mechanism cannot be exercised. Fix: name it in TN-17's powers channel (operator-signed, journaled as the declared control-action subtype).
22. **AD-13's regression-threshold rule is not carried.** *"each benchmark's regression threshold is stated when its baseline is recorded, as a multiple of measured run-to-run variance."* TN-23 records baselines and calls them the regression gate without the threshold rule. Fix: one clause in TN-23.
23. **The drift → stand-down path is never drilled.** TN-10's unexplained-live-drift stand-down is the node's sharpest automatic money control; A11 makes demo drift alarm-not-halt during the soak, and TN-23's checklist contains no drift stand-down fault-injection item. Fix: add one — an injected residual on a non-live binding drives the entry stand-down and only an operator `resume` after a fresh review clears it.

## LOW

1. TN-6 writes `cancel` where AD-27's command kind is `cancel_order` (the other four are spelled correctly).
2. Bare "calendar" survives in a few operational phrases ("calendar refresh", "calendars and tzdata verified", "explicit calendar and extension registration") against the parent's three-named-kinds convention; the substantive TN-14 row is correct.
3. AD-27's `denied-locally` outcome never appears in the node spine, so the adapter-pre-submission-check outcome and the authority-layer veto refusal are not visibly separated on the node's own path (TN-6's veto/suppression split is otherwise right).
4. B-1's door-parity contract test is inherited without scoping: the CLI carries every capability while the HTTP door carries two channels, so "identical function surface across doors" needs a declared parity scope.
5. TN-11 narrows AD-28's sensing-outage rule (*"fails closed until the same feed gap-replays"*) to "fails closed for entries" — the right reading under L39, but it should cite L39 as the narrowing authority.
6. TN-21 declares `world = replay` where B-7 derives world from data provenance ("never caller-declared"); the result is the same, the mechanism is stated backwards.
7. TN-19 says "the node's composition root holds the `WriterId` for Bot-domain record streams" without citing QL-1's declared writer unit `(machine, authoring role, kind)`.

---

## Summary

| Tier | Count |
| --- | --- |
| Critical | 4 |
| High | 11 |
| Medium | 23 |
| Low | 7 |
| **Total** | **45** |

**Gate recommendation:** do not hand this spine to `bmad-create-epics-and-stories` until C-1 through C-4 and H-1 through H-7 are amended at the desk. C-3 in particular changes which repository the largest epic lives in. Nothing found here requires re-opening an operator ruling; the four criticals are all cases where the node either lost half of a parent clause (C-1), never imported one (C-2), asserted a relocation the register contradicts (C-3), or stated a mechanism and its own refusal in one rule (C-4).
