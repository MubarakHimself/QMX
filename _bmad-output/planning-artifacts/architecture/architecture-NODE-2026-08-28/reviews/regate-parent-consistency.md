# Re-gate — LENS: parent / sibling consistency (SECOND PASS, fresh lens)

**Subject:** `architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md` (951 lines, TN-1..TN-25, status `draft`) + `.memlog.md` (50 entries).
**Against:** QMF parent spine AD-1..AD-41 (`architecture-QMX-2026-08-19`), QMB B-1..B-15, QML QL-1..QL-10, `docs/constitution.md` L1-L39 (incl. L30's 2026-08-21 roster-scope annotation), PRD FR-046 + §3 + §6, and the ratified `docs/` corpus (CT-22 v2 / CT-23 v2, DEC-0185 veto-round riders).
**Question:** does any sentence in the CURRENT text weaken, contradict, re-derive or silently amend an inherited rule — and did the fix pass introduce anything new?
**Date:** 2026-08-28. Reviewer: parent-consistency, second pass (fresh lens, not the first-gate seat).

---

## Verdict

**DO NOT RATIFY AS-IS — two criticals and eight highs, all closable at the desk, none needing the operator.**

The fix pass is real work honestly done. **Every one of the first gate's four criticals is closed, and closed correctly**, not papered over:

- **C-1 never-auto:** TN-7 now reads *"`suspend_new` and `drain` are `never-auto` — they stand until an operator `resume`, and a `reconciled` verdict never clears them. `flatten` satisfies only on `scope-flat-at-reconciled-verdict`; a command outcome never satisfies an intent."* The matrix cell now carries effect + typed scope + **satisfaction predicate**, and the KSA fold is explicitly monotone within a level epoch, lowering only on an operator `resume`. AD-36 is honoured verbatim.
- **C-2 `state_carry`:** now rides TN-9 (paper flip), TN-18 (any config version touching a Book/BMS identity-bearing field), TN-20 (two operator-signed acts, never inferred from one another), TN-22 (roster) and TN-25 (every binding the node mints), each with the `carries-ledger` signature and the `invalid input` refusal on absence. AD-29/AD-30/AD-41 satisfied.
- **C-3 transport locus:** TN-11 now declares the socket/framing/encoder/submit path a **`qmf-venue` increment completing its existing `ConnectionManager`**, keeps `protobuf` a qmf-venue-only dependency, mints no second connection manager and no second in-memory secret holder, and records the `VenueClientPort` question as a *candidate AD-28 annotation* rather than settling it. AD-26/AD-28/`DEPENDENCIES.md:47` satisfied; A36/A37 flagged.
- **C-4 cross-world replay read:** TN-21 now names **one sanctioned one-way replay import port** reading from the evidence tier, "the single exception to AD-19's cross-world refusal, and there is **no write exception, ever**", with `world` a component of `BotStateScope`. Surfaced, not smuggled.

Also verified closed: netting|hedging at bind time and at dispatch (TN-22/TN-6/TN-25); virtual (Book) vs venue position named apart, with the kill-line series marked to market per binding and `book_capital` (period-open, ex-unrealized) confined to the sizing ladder (TN-8/TN-25/TN-11); AD-37's collapse, compose and standing invariant (TN-6); AD-35 `disposition` as a mandatory field with the market-risk vs capital-authority classification (TN-7/TN-8/TN-9); AD-31's risk-domain writer `(machine, risk role, binding)` and the dispatcher's block-on-unpersistable (TN-2/TN-6); AD-31 cross-role reads declared at the door (TN-17); AD-24 heavy-by-default sequenced against the rung baseline (TN-19/TN-23); AD-27's two-path `resolve_unknown` with out-of-lookback routed to attestation (TN-6/TN-10); the fold-contract declaration and the rank-not-`WriterId` rule (TN-10); `decision_freshness_bound`, `instrument_class`, the treasury boundary-event kind, the sealed period's final look, B-3's derived-fragment discipline, AD-13's regression-threshold rule, the civil-time bucket-key carve-out, the two-tick-source edge posture, node stand-down vs binding `stood-down`, and the value/responsibility split in TN-6's do-not-default roster.

**The CLI question is cleanly and completely resolved.** Grep-verified across all 951 lines: no `qmn` command survives anywhere — the wizard is `just node-secrets-provision`, bootstrap `just node-data-bootstrap`, deploy `just node-install / node-switch / node-rollback`, replay `just node-replay`, config `just node-config-init/validate/explain`, registration moved to "the registration capability on the doors". Correction 5 is restated as SETTLED, TN-1 says the reconciliation note is **WITHDRAWN**, the Stack row marks `click` **NOT TAKEN**, and PRD FR-046 / DEC-0159 / DEC-0185 Ruling C stand unchallenged. **No stale reconciliation note survives, and no contradiction with FR-046 remains.** Banned vocabulary is clean except one slip (M12): zero "engine"/"kernel"/"plugins"/"minimal core"/"timeframe" outside the convention row, zero "paper node" outside the prohibition itself, "the trading node" with modes `paper | live` held throughout.

What follows is what the current text still gets wrong. **Findings RC-1, RH-1, RH-4 and RH-8 were introduced by the fix pass** — the flag the brief asked for.

---

## CRITICAL

### RC-1 — The AD-27 UNKNOWN block has been folded into the entry-side-only law; the parent explicitly excludes it, and TN-6 contradicts itself in two adjacent bullets *(NEW — introduced by the fix pass)*

**Where:** TN-6 bullet 1 vs TN-6's protection-gate bullet; TN-23's soak checklist; TN-24 (c); against TN-4's own shutdown rule.

**Spine sentence A (TN-6, entry-side-only law):** *"Every block the node can raise on a command stream — startup-reconciliation gating, a rotation-store failure, an unpersistable sink, a partial write, **an outstanding UNKNOWN**, node stand-down, a clock band, a full disk — refuses `place_order` and any risk-increasing `amend_protection` and NOTHING ELSE. **It never refuses `cancel_order`, `close_position`, `close_all`, a risk-non-increasing `amend_protection`, a CT-23 `close_full` or `tighten_protective_stop`**, or the recording of evidence."*

**Spine sentence B (TN-6, protection gate, eleven lines later):** *"Risk-reducing commands **pass it unconditionally** and dispatch ahead of `place_order`. **Its one legitimate hold is AD-27's per-command UNKNOWN block, which does hold protection commands** — and under it a protection act never evaporates: it stands as an AD-36 protection intent…"*

**Parent sentences:** AD-27 — *"While an `UNKNOWN` is outstanding on a command stream, the adapter refuses new commands on that stream (`transient venue failure`, after-condition = resolution); **protection commands are not exempt from the block** — but a protection act the block refuses never evaporates."* AD-36 — *"(The spine's one non-control block is AD-27's per-command `UNKNOWN` block — **venue uncertainty, not a control**: it carries its own `resolve_unknown` path and, as amended, never discards a protection intent.)"* L35 — *"an UNKNOWN blocks its command stream until an explicit recorded resolution."*

**What:** the fix pass, closing first-gate H-6, enumerated every node block as entry-side-only and swept the UNKNOWN block into the list. But AD-36 carves that block out of L39 *by name*, precisely because it is not a control — it is venue uncertainty, and dispatching a `close_position` into a stream whose last submission's fate is unknown is how a position gets double-closed. Sentence A is a silent amendment of AD-27 and L35; sentence B is the parent rule. Both are live.

**Why it matters:** three of the four places pick the wrong half. TN-24 (c) says *"UNKNOWN per L35, with the entry-side block…"*, and TN-23's acceptance gate would **certify** the violating behaviour: *"a forced disconnect mid-order mints UNKNOWN, **blocks the stream entry-side only while an exit still passes**, and a `resolve_unknown` clears it."* TN-4's shutdown rule assumes the opposite — it mints UNKNOWNs for every in-flight command *"so L35's stream block survives the restart"*, which is only meaningful if the block is a stream block. A builder reading TN-6 alone wires a node that closes into venue uncertainty; the soak gate then passes it.

**Fix:** remove "an outstanding UNKNOWN" from TN-6's entry-side-only enumeration and add one sentence: *"AD-27's per-command UNKNOWN block is **not a control and not an entry-side block** (AD-36 names it the one non-control block): while an UNKNOWN is outstanding on a `(VenueId, account)` stream, every command on that stream is refused, protection commands included, and a refused protective act stands as an AD-36 protection intent journaled before dispatch and re-decided when the block clears (re-deciding is not retrying). Only `resolve_unknown` clears it — never a reconciliation verdict."* Correct TN-24 (c) to match, and rewrite the TN-23 item as: *"a forced disconnect mid-order mints UNKNOWN and blocks the whole stream; a protective close issued under the block is journaled as a standing protection intent and dispatches on resolution — never refused-and-lost, never dispatched into the uncertainty."*

### RC-2 — The venue-resident protective stop is never attached; three of the node's safety arguments rest on it

**Where:** TN-6 (door order, command mint, submit) contains no protective-stop attachment rule; TN-11 names *"protective-stop attachment form per order type"* only as a CT-18 capability row. Grep-verified: "attach" appears in no order-path rule; "venue-resident" appears twice, both times as a consumer of a mechanism nothing mints.

**Parent sentence (AD-33):** *"**The protective stop attached at entry is Book-owned for the position's life** … Where CT-18 declares protective-stop attachment, **every live order attaches a venue-resident stop at placement — the only protection that survives a dead node, a dead connection, or an outstanding `UNKNOWN`**; where a Book requires attachment and the venue does not declare it, **placement is an `unsupported capability` refusal rather than a silently unprotected order**."*

**Spine sentences that depend on it:** TN-4 — *"the **venue-resident protective stop (AD-33) carries the position** meanwhile"* (the full-disk argument). TN-7 — *"**A dead node is answered by the venue-resident protective stop** (AD-33)"* (the dead-wire argument). TN-4's stand-down and shutdown contracts both turn on positions being protected while the node is quiescent, and the shutdown contract's licence to never flatten depends on it.

**What:** the node's entire "it is safe to stop accepting, to stall on storage, to stand down, to shut down without flattening" argument is built on a stop the order path never places. TN-6 walks the door ladder, resolves the execution target, mints the command and submits — and never says an entry carries a stop.

**Why it matters:** this is the only protection that survives every failure mode TN-4/TN-7 enumerate, and nothing in TN-23 would catch its absence. It is also where AD-34's placement-form fact lands (absolute protection is not supported for MARKET orders on this platform), so omitting the rule omits the one venue quirk that decides how the stop is expressed.

**Fix:** add to TN-6, at command mint: *"Where the Book's `exit_policy` requires protective-stop attachment, every `place_order` carries a **venue-resident protective stop at placement**, in the form CT-18 declares for that order type (AD-34: the entry-relative form where absolute protection is unsupported for MARKET orders, the reference price being declared CT-19 surface). Where the Book requires attachment and CT-18 does not declare it, **placement is an `unsupported capability` refusal — never a silently unprotected order**. Because the resting stop may then differ from the declared full-loss price by slippage, AD-40's declaration stays the plan and is never read back as the observed fill."* Add a TN-23 checklist item: an entry on a Book requiring attachment refuses where the capability is undeclared, and a placed entry is observed carrying its venue-resident stop.

---

## HIGH

### RH-1 — `resurrect` is a control action nobody minted *(NEW)*

**Where:** TN-4 (*"left **ONLY by an operator `resurrect`** act through the powers channel, **journaled as an operator control action at global scope**"*), TN-17's powers list, the Conventions row, Deferred — 14 occurrences. The "Parent annotations and mints proposed by this sitting" section proposes no CT-30 kind.

**Parent sentence (AD-36):** *"**Control-action contract (CT-30):** typed action kind, **addable never redefined and each defined once here** — `suspend_new` … `drain` … `flatten` … `resume`; the issuing authority and its kind, enumerated … a subject scope … **a mandatory satisfaction predicate** … and an evidence record."*

**What:** TN-4 says in one sentence that node stand-down is *"not a CT-30 control action"* and in the next that its exit is *"journaled as an operator control action at global scope"*. Either `resurrect` is a new CT-30 action kind — legal under addable-never-redefined, but a parent-contract mint a child may not assert — or it is a node-local lifecycle record that journals as an AD-21 `control action` **event type** under a declared subtype (the pattern AD-21 already licenses for the sealed period's one final look). The text supports both, and the CT-30 reading arrives with no declared satisfaction predicate and no row in CT-30's pinned authority→close-reason table.

**Fix:** take the second reading and say so in TN-4: *"`resurrect` is a node lifecycle act, not a CT-30 control action; it journals as an AD-21 `control action` **event** under the declared node subtype `node_resurrect`, carrying the operator signer and global scope, and mints no CT-30 record."* Add that subtype to the parent-annotations section as a doc-factory mint, beside the Records↔CT-13 bridge. If instead a real CT-30 kind is wanted, propose it there explicitly with `never-auto` as its predicate.

### RH-2 — `admission_impact` is declared and never wired: a settings edit can re-version a Book past AD-32

**Where:** TN-18 (template discipline: *"every variable flagged `ui-editable` or `uneditable` with its `admission_impact`"*; the value-home rule repeats the field); TN-17 (*"settings edit, which mints a new config version and schedules a restart at a safe point"*); TN-18's versioning bullet (mints a new AD-29 binding, collects `state_carry`).

**Parent sentence (AD-30):** *"Each variable **also declares `admission_impact` ∈ `resign | relint | none`**, so an edit's cost is stated rather than argued: changes touching `charter`, `money_rules`, `admission_bar` or `required_venue_capabilities` are **`resign` (a fresh AD-32 Layer 2 + Layer 3)**; `leash_grammar`, `control_policy` and `protection_windows` numbers are `relint` (Layer 1 only)."*

**What:** the node carries the flag as schema and never acts on it. The whole edit flow — powers channel → new config version → new binding → `state_carry` → restart at a safe point — never re-runs admission. An operator edits `money_rules` through the settings surface and the node binds the new Book version to live money at the next boot on a signature that attested the superseded fingerprint: the exact failure AD-18's Book-definition-fingerprint identity field exists to prevent.

**Why it matters:** it is the one path by which live money moves under rules no admission ever saw. TN-20's precondition battery guards *promotion*, not re-versioning, and TN-18's `state_carry` collection guards the *money carry*, not the *rules*.

**Fix:** add to TN-18: *"A config version's `admission_impact` is enforced, not merely declared: a diff touching any `resign` variable makes the resulting binding inadmissible to `role = live` until a fresh AD-32 Layer 2 (demo shakedown) and Layer 3 (one operator signature on the assembled page) complete; a `relint` diff re-runs Layer 1 at compile; `none` needs neither. The compiler derives the impact from the registry rows the diff touches and stamps it on the config version."* Cross-reference from TN-17's settings-edit power and from TN-20's battery.

### RH-3 — QL-7's advisory stop proposal and DEC-0185's adopt-the-bot's-stop mode are absent from the node that must host them

**Where:** grep-verified — "advisory" and "proposed_r" occur **zero** times in the spine. TN-6 says only *"the declared full-loss price derived by the per-family `ExitLogicModule` (`door.py:469`, DEC-0142)"*; TN-19's seat contract has callbacks *"return zero-or-more CT-23 intents"* with no mention of the field.

**Parent sentences:** QL-7 — *"The bot's entry proposal carries an **advisory stop proposal** — a proposed protective-stop price or `PriceDelta` bound, advisory exactly as `proposed_r` is … The declared full-loss price is derived at the Book door … **consuming the advisory proposal** and the intent's cited evidence."* `docs/contracts/ct-23-risk-evaluation.yaml:42` (format version 2) — *"`entry.advisory_stop_proposal`: an OPTIONAL advisory protective-stop proposal … a Book MAY declare the CT-22 **adopt-the-bot's-advisory-stop module mode** that honors the proposal as-is (validated against the Book's risk rules), so **bot-owned exit methodologies are first-class**"* (DEC-0185 — the operator's own veto-round rider; mirrored at `ct-22-book-charter.yaml:31` and `qmf-risk.md:95`).

**What:** the node is the runtime that wires CT-23 and executes `ExitLogicRef`. It carries the authority half correctly (`requested_r` Book-resolved, full-loss price Book-derived) and drops the bot's declared channel entirely. A builder wiring TN-6's door from this text gives the `ExitLogicModule` no advisory input and cannot implement the adopt mode at all — so a bot carrying its own exit methodology is silently overridden, which is precisely the outcome the operator's veto round reversed.

**Fix:** in TN-6's Book-door bullet: *"The CT-23 v2 entry intent carries the bot's optional **`advisory_stop_proposal`** (a `Price` or `PriceDelta` bound) alongside its advisory `proposed_r`; the Book door's per-family `ExitLogicRef` consumes it when deriving the declared full-loss price, and a Book may declare the ratified **adopt-the-bot's-advisory-stop module mode** — honouring the proposal as-is, validated against the Book's risk rules — inside the existing `{module_id, config}` shape (DEC-0185 / DEC-0177). No inbound-refusal posture exists; `requested_r` stays Book-resolved."* Name the field in TN-19's seat contract too.

### RH-4 — TN-2 and TN-4 disagree on whether a preflight failure exits *(NEW — both halves added by the fix pass)*

**Where:** TN-2 act 1 vs TN-4's crash-loop bullet.

**Spine sentence A (TN-2):** *"Fail-closed with a typed failure id, journaled, and **the node stays alive in stand-down with the doors serving — it does not exit into a restart loop**."* Reinforced above: *"Only a failure that prevents the doors themselves from binding exits non-zero; every later failure boots into stand-down-alive."*

**Spine sentence B (TN-4):** *"The crash-loop fold counts BOOT ATTEMPTS BY STAGE … K attempts within T seconds … **A loop in preflight therefore trips `(K, T)` exactly as a loop in compose does.** **`StartLimitBurst` MUST exceed K so systemd performs the restarts that carry the node to the boot which self-detects the loop**."*

**What:** if a preflight failure never exits, there is never a second attempt, so `(K, T)` can never trip in preflight and the `StartLimitBurst > K` requirement governs nothing; if preflight failures do exit and restart, TN-2's "does not exit into a restart loop" is false. The two halves of the memlog's supervision ruling (11) were applied to two TNs without being reconciled.

**Why it matters:** TN-16 pins `StartLimitBurst` / `StartLimitIntervalSec` into a checked-in unit file, and TN-23's acceptance item — *"a crash-loop and a preflight failure each boot into stand-down with the doors serving"* — cannot be written until this is settled.

**Fix:** state the model once, in TN-4, and cite it from TN-2: *"A failure at or after preflight does not exit — the node enters stand-down alive with the doors serving, and no systemd restart follows. The crash-loop fold therefore governs only failures that DO exit: a failure to bind the doors, and any unhandled process death after boot. It counts boot-attempt records by stage across boot epochs; `StartLimitBurst > K` with `StartLimitIntervalSec ≥ T` keeps systemd restarting long enough for the fold to see the pattern, and a door-binding failure that trips `(K, T)` is the one case that ends at `start-limit-hit` with no doors — an alarm on the dead-man's switch, not a stand-down."*

### RH-5 — The soak is demo-only for a full week, but the live binding at its end needs a live-conditioned baseline

**Where:** TN-9 (*"for one full unattended week the node runs in paper mode on the demo account … **Live binding only at the end of that week**"*) vs TN-8 (*"the live binding's baseline is minted from **live-connection recording during the warm-up week**"*), TN-10 step 9, TN-23.

**Parent sentences:** AD-39 — *"**A live binding requires a present baseline artifact** — checked at AD-29 bind time and named among AD-32's Layer-2 prerequisites — so the order is: warm up, mint the baseline, then bind live."* AD-29's bind-time check additionally requires the live-path rung baseline on the deployment tuple.

**What:** TN-8 keys the baseline `(VenueId, environment, instrument)` and rules — correctly — that a demo-conditioned baseline never satisfies a `role = live` binding. But TN-9 describes the week as running *on the demo account* and never says the **live connection is also established and recording throughout**. TN-11 declares `required_connection_count = 2`, so it is possible; nothing says it is required. Read one way the live baseline accumulates all week and the bind succeeds; read the other way the week records only demo ticks and the live bind refuses on day eight for a reason the checklist never surfaces.

**Why it matters:** it is the last gate before live money and the only one with a week-long lead time. TN-23 proves the *refusal* (*"a demo-conditioned baseline is proven NOT to satisfy a `role = live` binding"*) and never proves the *minting*. It also silently moves live credentials, Spotware approval and KYC from week-eight prerequisites to soak-entry prerequisites.

**Fix:** state it in TN-9: *"The soak runs BOTH connections: the demo connection carries paper routing and the full order-path machinery; the **live connection is established for sensing and recording only — no live binding, no command stream open** — so the live-environment SQS baseline and the live-path rung baseline accumulate across the same week that proves the machinery. Live venue credentials, Spotware approval and KYC are therefore soak-entry prerequisites, not week-eight ones."* Add the matching TN-23 item (a live-conditioned baseline is present and satisfies the bind-time check at week's end) and adjust the Deferred row's timing note.

### RH-6 — The alert allow-list is widened past PRD §3's closed ratified list with no reconciliation note

**Where:** TN-15's three classes, the dead-man's switch, the liveness digest and the soak digests; against the node's own inherited row *"PRD §3 notification allow-list and the two-plane rule; unattended-operation doctrine | prd.md:119-127 | TN-15"*.

**Parent sentence (PRD §3):** *"notifications fire only on a **closed, ratified event-class allow-list** — sweep, re-seed, refund, kill-switch/KSA events, and supervision fail-closed; **everything else is console evidence, never a push**."*

**Spine sentences:** *"(3) **SILENT DEGRADATION** … a clock band at `no-new-entry` or worse; an unexplained live-drift entry stand-down on any binding; a failed news-calendar refresh; a degraded or dead canonical sensing feed; a failed nightly backup, sample restore, full restore or host-loss rehearsal; disk headroom below `disk_headroom_min`; a live first-connection or data-quality verification failure."* Plus *"A **liveness digest survives go-live**; it is the one scheduled push that is not a failure"* and the soak-scoped demo-drift digest.

**What:** the node adds a whole event class and two scheduled pushes to a list the PRD declares closed and ratified. The reasoning is sound — an unattended node that silently stops trading is the failure the doctrine exists to prevent, and the two-plane rule is honoured throughout — but the node binds PRD §3 in its own inherited table and then widens it **by assertion**, which is exactly the move TN-1 refused for L30 and TN-11 refused for AD-28.

**Fix:** keep the mechanism and add a row to "Parent annotations and mints proposed by this sitting": *"**PRD §3 notification allow-list — proposed widening.** The closed list covers money boundaries and protection escalation but not silent degradation: an unattended node that has stopped accepting entries, or cannot persist evidence, for a non-KSA reason emits nothing. This sitting proposes a third ratified class (enumerated in TN-15), plus an external dead-man's switch and a liveness digest, as a PRD amendment carried by the documentation factory — surfaced, never settled here."*

### RH-7 — AD-40's no-scale-in refusal is missing from the one TN whose Prevents line names it

**Where:** grep-verified — "scale-in" appears zero times. TN-24's Prevents reads *"a second way for size to move"*; TN-6's door ladder and TN-25's virtual-position fold never refuse an addition to an open position.

**Parent sentence (AD-40):** *"**V1 admits no scale-in: adding to an open position is a `policy rejection`**; a second tranche needs its own admission and its own R, which is a later Book version, never a quiet widening of this one."* Sibling B-12 enforces the analogue in the tunnel (*"at most ONE open position per (venue, instrument) — violation is the typed refusal DuplicatePositionStream"*).

**What:** the node is the only runtime where a live bot can mint a second entry against an instrument it already holds. On a netting account the venue will happily add to the account-level position; the virtual-position fold then carries two admissions with two frozen R faces against one venue position, and every `r_multiple`, bench predicate and kill-line mark inherits the ambiguity. AD-40 rules it a refusal; the node never raises it.

**Fix:** add to TN-6's door ladder (before sizing), restated in TN-25: *"**No scale-in (AD-40).** An entry intent against an instrument on which the binding already holds an open **virtual position** is a `policy rejection` at the door — a second tranche requires its own admission under a later Book version. The check is stated over virtual positions, so a netted account's shared venue position never masks it."* Add a TN-23 checklist item.

### RH-8 — TN-18's "invocation" precedence layer has no surface left after the command line was ruled away *(NEW — exposed by the fix pass)*

**Where:** TN-18 — *"It is compiled from explicit layers with fixed precedence — **invocation**, then the deployment roster …, then the BMS fragment, then the Book fragment, then node defaults."*

**Sibling sentence (B-3):** *"compiled from explicit layers with fixed precedence: **invocation flags** > run spec > BMS config fragment > Book config fragment > workspace defaults."* B-3's invocation layer is the `qmb` CLI's flags — a surface that exists.

**What:** the node inherited B-3's layer stack verbatim and then deleted the only surface that could supply its top layer. TN-17 rules that config authoring is toolkit recipes over library functions and that the UI edits the artifact through the powers channel; neither is an "invocation". A builder must invent one — environment variables on the unit file, `ExecStart` arguments, a kwarg on the compile function — and whatever they invent becomes the **highest-precedence, lowest-visibility** source of money-path values, sitting above the roster and outside the powers-channel edit flow that collects `state_carry` and enforces `value-status`.

**Fix:** delete the layer — *"the node's compile has four layers: roster, BMS fragment, Book fragment, node defaults; there is no invocation layer, because there is no command line and no runtime override path"* — or define it narrowly and audibly: *"invocation is limited to the check-mode and dry-run entry points (TN-16), may supply no value that gates live money, and is stamped on the resolved artifact as `invocation_overrides`, a live boot with a non-empty set refusing."* The first is cheaper and safer.

---

## MEDIUM (16, rolled into counts)

1. **`close_partial` / partial exit.** AD-33: *"`close_partial` is not a V1 kind … a Book- or bot-scoped **partial exit is an `unsupported capability` refusal in V1**."* Zero occurrences; TN-6 wires the CT-23 door without it.
2. **AD-34's placement form.** The entry-relative path for MARKET orders, the reference price as declared CT-19 surface, and *"AD-40's declaration stays the plan and is never read back as the observed fill"* are absent (RC-2's fix carries them).
3. **Shutdown-minted UNKNOWNs have no AD-27 trigger.** TN-4 mints an UNKNOWN per in-flight command at SIGTERM *before* closing sessions; AD-27's UNKNOWN observation carries a trigger from `timeout | transport-error | disconnect`, none of which has occurred. Declare a `lifecycle-stop` trigger as a proposed CT-20 mint, or order the mint after session close so `disconnect` applies honestly.
4. **`resolve_unknown` must itself be an observation.** AD-27: *"unblocking is an explicit typed `resolve_unknown(…)` call by the application, **itself recorded as an observation**."* TN-6 says only that it "journals the resolving evidence".
5. **The promotion card's other identity fields.** AD-18 requires the **Book- (or BMS-) definition fingerprint as an identity field**, so a signature can never attest a superseded template; AD-32 Layer 3 requires one assembled page carrying both proofs, the binding identity, the capability-satisfaction result and the resolved BMS fingerprint. TN-20 carries only the plain-words summary and the battery's rendered outcome.
6. **Two names for one floor.** AD-40: *"`loss_floor` is **the same number the kill line names** — one value, one name."* TN-8/TN-25 make `kill_line_capital_floor` canonical and say the node mints no second name — yet the corpus now holds two. Add a parent/registry annotation recording them as one variable with one canonical key.
7. **AD-37's arbitration mechanics, partly carried.** TN-6 has collapse, compose and the standing invariant; it omits *"arbitration resolves **strictly by rank with no arrival-order input**"* and Tier 1 (*"venue-resident actions sit outside the ordering by construction"*).
8. **Replay's spread / SQS input is unspecified.** B-2: *"In non-live runs the Book's SQS door (AD-39) reads this run's modeled-spread series as its spread input."* TN-21 has no fill or spread model by design, so what the SQS door reads under replay is undefined — and TN-21's diff is the regression gate for every order-path change.
9. **"Ratified by adoption" while narrowing.** TN-10 says the PRD's mined doctrine *"is ratified by adoption"*, then narrows *"Unexplained live drift halts trading"* to an entries-only stand-down (A12). The narrowing is right under L39 — name it and cite L39 at the point of use, exactly as TN-11 does for the sensing-outage rule.
10. **Two age bounds, relation unstated.** TN-19's heavy-labeler fan-out is *"consumed under a declared maximum age"*; AD-39/TN-8 make `decision_freshness_bound` the Book's mandatory non-defaultable bound on SQS input age. Whether the snapshot's max age must be ≤ `decision_freshness_bound` is never said.
11. **`connectivity` / `unknown_state` disposition.** TN-7 classes them *"market-risk blocks on the affected stream and `blocks-paper` **there**"*. AD-35 rules live and demo distinct `(VenueId, account)` streams whose uncertainty never gates each other, and warns that a silent paper outage corrupts every later decay verdict. Say plainly whether a connectivity escalation on the live connection blocks paper routing to the paired demo account.
12. **Banned-vocabulary slip.** TN-24 (j): *"a venue **stop-out** or margin liquidation"* — in the same sentence that says *"(the bare phrase is never used)"*. AD-41/Conventions: the bare word is used nowhere. Rewrite as *"a venue margin liquidation (`venue_liquidation`) or a venue-initiated close"*.
13. **Absent-or-terminal subject at submission.** AD-27: *"a command whose subject is absent or already terminal at submission resolves **without submission**, never as a naked close."* TN-24 (j) covers the post-submission race only.
14. **The third satisfaction predicate.** TN-7 carries `never-auto` and `scope-flat-at-reconciled-verdict`; AD-36's closed vocabulary also holds `no-pending-orders-at-reconciled-verdict`, which the matrix's mandatory predicate cell should be able to express.
15. **Acknowledgement mode named, rule not carried.** TN-11 lists the CT-18 field; AD-27's consequence — *"an outcome is never derived from absence alone"*, with the cancel/read-back rule — appears nowhere on the node's own outcome path.
16. **"Sealed" is undefined in TN-21.** *"a named one-way REPLAY IMPORT PORT — read-only, **refusing any observation not yet sealed**"*. Sealed by the composition seal (TN-2), by AD-21's 12-month split seal, or by durable verified persistence? Under the 12-month reading, TN-23's *"a replay of a recorded soak day diffs clean"* is illegal. Say which.

## LOW (4)

1. TN-15 ships the Prometheus/Grafana/Loki stack that PRD §6's terminal anti-goals forbid the console to *clone*. Consistent (use it, don't rebuild it) — one clause would keep the UI sitting from reading a mandate to render dashboards.
2. Bare "calendar" survives in operational phrases (*"calendar refresh"*, *"calendar age"*, *"calendars … verified"*) against the three-named-kinds convention; TN-14's substantive row is correct.
3. AD-37's *"a lower-ranked action may never undo a higher-ranked one"* is not carried into TN-6's arbitration clause (its converse standing invariant is).
4. TN-9 declares the deliberate collapse of AD-9's `paper-validation` / `paper-benched` roles onto `demo` with the consequence stated — good — but the later role split appears in no Deferred row.

---

## Summary

| Tier | Count |
| --- | --- |
| Critical | 2 |
| High | 8 |
| Medium | 16 |
| Low | 4 |
| **Total** | **30** |

**New contradictions introduced by the fix pass:** RC-1 (the UNKNOWN block folded into the entry-side-only law — the most consequential, because TN-23 would certify it), RH-1 (`resurrect` as an unminted control action), RH-4 (TN-2 vs TN-4 on whether preflight failure exits), RH-8 (the orphaned invocation layer, exposed by the no-command-line ruling).

**Not findings, recorded so the next pass does not re-open them:** the CLI question is fully closed, with no residue and no FR-046 conflict; all four first-gate criticals are correctly closed; `qmn`-as-code-name, the operations toolkit, the observability stack as a separate zero-authority system, the soak-as-warm-up-week and the promotion click are applied consistently with the operator's four rulings and correctly tagged A1/A10/A17/A26 in the register.
