---
review: reconcile — rulings fidelity
target: ARCHITECTURE-SPINE.md (risk increment AD-29..AD-41 + cross-AD amendments)
authority: .memlog.md entries 84–117 (risk sitting = 91–117); secondary: research-risk/brief-*.md delegated proposals
sitting: QMX risk sitting 2026-08-20
reviewer: rulings-fidelity reconcile pass
date: 2026-08-20
verdict: PASS WITH FINDINGS — 2 material, 2 medium, 6 low
---

# Reconcile review — risk increment rulings fidelity

## Verdict

Every operator ruling from the risk sitting reached the spine, and the eighteen quiet
requirements this pass was told to hunt are all present in recognisable, load-bearing form —
but **two rulings did not land as the operator stated them**: the bench counter's *what counts*
half was quietly broadened from "exits at ~full planned loss" to "any strictly-negative close"
(AD-41), and the operator's **source-authority order for risk** (GitBook + trading-node docs
authoritative, QMX-discussion barred) is **absent from the spine entirely** while the phrase
"Authority order" in the Inherited-invariants table is occupied by a *different* ruling, so the
omission reads as landed. Four smaller items are weakened or dropped, and one — the entity-journal
deepening — is a defensible mechanism substitution that the spine states without disclosing that
it substitutes, and is flagged for the operator per instruction.

Nothing ratified was inverted. No ruling was reversed. All findings are additive fixes.

---

## Part A — The eighteen quiet requirements

### 1. "Configurable" always = UI-editable, declared per variable in templates

**Ruling:** memlog 103 (STANDING GLOBAL RULE) — "everywhere the operator says 'configurable', it
means configurable IN THE UI; every configurable variable minted anywhere in QMX must surface as
UI-editable at platform level. Applies to SQS thresholds, bench counters, dead-zone widths, paper
balances, news buffers, everything."

**Landed where:**
- Inherited invariants row, L35: *"Configurable means UI-editable at platform level"* → AD-30 template flags; AD-34/38/39/41 variables.
- AD-30, L325: every declared template variable carries a `ui-editable | uneditable` flag, with the standing rule quoted.
- Conventions, L526: *"every configurable variable minted anywhere declares `ui-editable` or `uneditable` in its template and carries a unit-kind … 'configurable' always means editable in the platform UI."*
- Per-variable, all five named classes: SQS parameters L449; bench threshold L479; dead-zone/news widths L430; paper balance L392; breakeven-ratchet trigger + offset L380.

**Verdict: LANDED IN FULL.** The rule landed three times over (inherited row + AD-30 mechanism +
global convention) and every one of the operator's five named examples carries it explicitly. This
is the strongest-landed ruling in the increment.

*Note (no action):* `admission_bar` thresholds (AD-32 L354), AD-37 rank fields (L417) and
`seat_loss_run_allowance` (AD-40 L467) do not restate the flag locally; they are template-declared
variables and are covered by AD-30's blanket + the Conventions row. Correct by construction.

---

### 2. Version ≠ copy — both concepts present

**Ruling:** memlog 100(2) — "VERSION is not COPY: version = template-level change (variables
changed/added, 'never the same'); copy = instantiation of a template/version onto an account —
both exist in the model." Seeded at memlog 93 ("defaults + versions + copies").

**Landed where:** AD-30, L326 — *"**Defaults + versions + copies.** A template version is grammar
plus defaults; a copy is that version instantiated onto an account as an instance. Adding a broker
account offers copies of the chosen defaults — Book instance, BMS instance, own connection.
**Version ≠ copy: a version changes the variables, a copy binds them to money.**"* The copy side is
reinforced at AD-29 L305 (an instance never spans venues; a strategy at several brokers is several
instances of one Book version).

**Verdict: LANDED IN FULL**, including the operator's distinguishing sentence almost verbatim.

---

### 3. News blackout stops live AND paper entries; suppressed-decision RECORDING continues

**Ruling:** memlog 97 — "an instrument under news blackout stops ALL trading on that instrument —
live AND paper, no exceptions ('I can't risk it. For now')… suppressed-decision journaling (A-7,
delegated PK-6) still records would-have-been actions — recording is not trading, decay sensing
keeps its data points." Mono-pair/multi-pair wrinkle delegated: block binds the instrument.

**Landed where:**
- AD-38 L431: *"An instrument under a news blackout stops **live and paper entries alike** (operator ruling). **The blocked decision is still journaled** — a `decision` event on the veto path carrying the refusing door, the would-have-been action, and the controlling window's fingerprint… Decay sensing therefore keeps its data points without a trade being placed."*
- AD-35 L389: *"Routing to paper is never a way around a control. A protection window blocks its instruments in paper exactly as in live (AD-38)… What continues under a control is the **recording**… Recording is not trading."*
- Multi-instrument wrinkle: AD-38 L433 — blocked only on the instruments in scope, others keep trading.
- Veto-path vs suppression-path split kept clean: AD-38 L438 (door-class refusal) vs AD-36 L407 (suppression = already-authorized action).

**Verdict: LANDED**, with one disclosed narrowing — see **Finding 8**: the operator said "stops ALL
trading", the spine says "blocks new entries … and nothing else" (never an exit, a protection
amendment, a protection action, or observation). The narrowing is safety-motivated, corpus-grounded
(CT-BMS-04 per memlog 113), openly stated in the AD, and matches this review's own brief — but the
spine nowhere records that the operator's words were broader.

---

### 4. Kill switch stops paper too; kill line is a different thing; operator flatten authority inalienable

**Ruling:** memlog 98.

**Landed where:**
- AD-36 L402: *"**Two different things, named apart, never merged.** The **kill switch** is the global black-swan authority: it **stops all trading including paper**, is sensor-fed (MIS and SQS are inputs, never authorities), escalates automatically and de-escalates only by a human. The **kill line** is a per-Book capital floor: breaching it automatically flattens that binding's scope and stands the Book down — **a 3am breach never waits for the operator**."*
- Flatten authority, AD-36 L404: *"(1) **The operator — always, at any scope, unconditional, never removable, never gated on reconciliation.** (2) Book policy, only through pre-declared trigger classes… (3) **Nobody else**…"* plus *"Every other money boundary — rollover, sweep, re-seed, paper flip — leaves positions alone."*
- `resume` operator-only, L405. Effect-per-severity is node authority, L408 (matches "which effect fires per severity = node authority").
- Cross-references: AD-35 L389 (kill switch stops paper too); AD-27 L278 (authority assigned in AD-36); AD-29 diagram L317 (*Operator — inalienable override*).
- Naming split held in Conventions, L524: kill switch vs kill line "never interchanged".

**Verdict: LANDED IN FULL**, all four halves (global-incl-paper / per-Book floor / auto-flatten at
3am / inalienable operator authority) plus the "every other boundary leaves positions alone" rider.

*Info:* the operator's "cuts off actual connection" phrasing was to be "recorded as evidence, not
bound" (memlog 98). It is not in the spine. Correctly non-binding — the memlog is its record. No action.

---

### 5. Breakevens never count toward the bench + recorded as their own metric

**Ruling:** memlog 99 — "breakeven exits do NOT count toward the bench… Breakeven exits recorded as
their own metric (clustering watch; reversible later from data)."

**Landed where:** AD-41 L477 — *"**Breakeven exits never count toward the bench.** … A breakeven cost
nothing, and a bench that fires on trades that cost nothing measures thesis quality where the leash's
job is damage. **Breakevens are recorded as their own metric** (clustering watch), which makes the
ruling reversible from evidence."* Reinforced: forced/boundary flats count only if they realized a
loss (same bullet) — "the system's own protection never benches the bot it just protected."

**Verdict: LANDED IN FULL** — both halves, plus the reversibility rationale the operator implied.

---

### 6. Bench threshold per-bot + configurable

**Ruling:** memlog 99 — "threshold is PER-BOT (2 = 'perfect' for a scalper) and emphatically
CONFIGURABLE (strategy-family-dependent: scalper vs holders vs crypto; bots may use multiple exit
methods) — typed + versioned + configurable, never hardcoded."

**Landed where:** AD-41 L479 — *"**The bench threshold is per-bot and configurable** (typed `count`,
UI-editable, strategy-family dependent — a scalper and a holder differ, and one bot may use several
exit methods). It is never a spine constant. Recorded corpus evidence, non-authoritative: a value of
two for a scalper, explicitly recorded as unusable until these semantics were settled."* Typed name
`bench_consecutive_loss_threshold [count]` minted at AD-40 L467.

**Verdict: LANDED IN FULL.** "Versioned" is not restated at AD-41 but is delivered by AD-30's
template version graph (any threshold edit mints a new Book version, L328–329). No action.

---

### 7. USD numeraire with `accounting_currency` still declared

**Ruling:** memlog 111(b) — "NUMERAIRE = USD, system-wide. Book charter **still declares
accounting_currency** so a later currency is a version change; non-USD bindings refused in V1
(config-level constraint, not ceremony)."

**Landed where:**
- AD-40 L463: *"**Numeraire is USD system-wide in V1.** The Book charter **still declares `accounting_currency`** so a later currency is a version change, and **binding a Book to an account in another currency is a `policy rejection`** — no rate source is ratified… The conversion seam ships; it switches on when a source is ruled."*
- AD-30 L331: every Book definition declares `accounting_currency` (AD-40).
- Deferred L589: cross-currency unlock awaits a ratified rate source.

**Verdict: LANDED IN FULL** — all three halves (USD system-wide / field still declared / non-USD
refusal), with the "seam ships, switch later" framing preserved.

---

### 8. BMS = account-facing, one per account, many Books; a Book binds one at a time, dated

**Ruling:** memlog 101 (refining 92) — BMS is the ACCOUNT-FACING supervising layer; bot N-1 Book;
Book binds exactly ONE BMS at a time (dated, swappable); one BMS serves MANY Books; **one BMS
instance per ACCOUNT**; authority split stays default v1 verbatim with the QMF migration caveat.

**Landed where:** AD-29 L302 — *"**The BMS is the account-facing supervising layer**, not a rulebook
beside the Book: **one BMS instance per account**, serving **many Books**; a **Book binds exactly one
BMS at a time** (dated, append-only, swappable — re-binding mints a new binding record with a
`supersedes` edge); a **Bot binds exactly one Book** (DEC-0115). Every cardinality-one here is a
deliberate ruling under AD-17, not an assumption."* Authority split verbatim + migration caveat at
L303. Several Books on one account share one BMS and one command stream — named, not hidden (L306).

**Verdict: LANDED IN FULL** on every cardinality. **Weakened on one rider — see Finding 5:**
DEC-0095's *"crypto/prop-firm variants = NEW BMS versions, never simultaneous stacking"* (memlog 92)
has no explicit clause; stacking is foreclosed structurally by "one BMS at a time" and variants-as-
versions is implied by AD-30's version graph, but neither is stated.

---

### 9. bot → Book → BMS → account chain, verbatim

**Ruling:** memlog 100(1) + 101 — operator: "the BMS, not the Book, connects to the account"
("understand the actual architecture, draw a bloody diagram"); constitution L1 verbatim in all three
legacy layers.

**Landed where:**
- Inherited invariants L34: constitution L1 as a standing row.
- AD-29 L301, verbatim and marked verbatim: *"Bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market. Hierarchy: bot → book → BMS → operator."* — *"Nothing in QMF may invert or shortcut it."*
- The bloody diagram, L309–318: `Bot → Book instance → (one at a time, dated) BMS instance → Account(role) → VenueId`, with a second Book binding the same BMS and the operator on a dashed escalation edge.
- Consumed downstream: AD-36 flatten authority L404; AD-37 rank derivation L417.

**Verdict: LANDED IN FULL**, including the diagram the operator explicitly demanded and the
account-facing direction he corrected.

---

### 10. Exit door risk-reducing-only + later-version delegation rider

**Ruling:** memlog 95 — Book owns exit policy; bots PROPOSE risk-reducing exits through a versioned
Book door (fast invalidation preserved); Book executes or refuses with recorded reason. RIDER: later
Book versions may delegate specific exit organs to specific bot families — "the door grammar is
versioned, delegation = a version change not a rule break."

**Landed where:** AD-33 L364–L367:
- L364: Book owns exit policy; a Bot may *propose* through a versioned door; Book executes or refuses with a recorded, journal-bearing reason.
- L365: *"**Exit intents are risk-monotonic by construction.**"* V1 kinds `close_full | close_partial | tighten_protective_stop`; may never widen a stop, extend a target, re-open, or increase size — `policy rejection`. A tighten names *a direction and a bound, never a price*.
- L367: *"Later Book versions may delegate specific exit organs to specific bot families — a **version change, not a rule break**."*
- Fast invalidation explicitly preserved (AD-33 "Prevents" line L362; AD-37 rank 3 L417).

**Verdict: LANDED IN FULL**, both the ruling and the rider, in the operator's own framing.

---

### 11. Breakeven-ratchet-only V1 for `amend_protection` + verify-or-refuse atomicity

**Ruling:** memlog 110 — fifth command `amend_protection` minted; cTrader facts CONFIRMED-PRIMARY;
amend atomicity UNDOCUMENTED = verify-or-refuse obligation; server-managed trailing = CT-18 capability
fact; market orders take relative SL/TP at placement; **V1 dynamic SL/TP = move-to-breakeven ratchet
only, risk-reducing, per-Book configurable**; richer policies = later Book versions.

**Landed where:**
- AD-34 L376: fifth command minted through AD-27's explicit-later-mint clause; risk-non-increasing at contract level; **never emulated by cancel-then-place**; never widened into a general amend.
- AD-34 L377: cTrader facts CONFIRMED-PRIMARY incl. one-message position amend, pending-order path, absolute-not-supported-for-MARKET (relative form is the declared path), no dedicated response message.
- AD-34 L378: *"**Amend atomicity is UNDOCUMENTED in every primary source**… a `measured-at-connection` CT-18 field under AD-28's verify-or-refuse posture: until the verification suite establishes it, a Book policy that depends on amending both protection sides in one act **refuses**, and single-sided amendment is the only legal V1 path."* Mirrored in AD-28 L288 and L293.
- AD-34 L379: venue-managed trailing is a capability fact, never assumed; declared-and-opted-in only; pushed changes enter as ordinary observations; closes carry `protection_amendment_fill`.
- AD-34 L380: *"**V1 dynamic SL/TP is the move-to-breakeven ratchet only:** one-directional, risk-reducing, never reset outward, per-Book configurable."* Trigger point + offset = configurable UI-editable, no spine value. Richer policies = later Book versions.
- AD-27 L273: vocabulary is now *exactly five kinds*; `amend_protection` dispatches ahead of `place_order` on shared throttles (L275).
- Deferred L592: general `amend_order` stays an explicit later mint.

**Verdict: LANDED IN FULL** — every clause of memlog 110, plus the cross-AD amendments memlog 117 promised.

---

### 12. Paper balance — family-scoped, configurable, resettable

**Ruling:** memlog 104 rider (2) — "paper starting balance = Book/family-scoped CONFIGURABLE default
(UI), resettable by dated operator action, sized for data-collection realism."

**Landed where:** AD-35 L392 — *"**Paper money is frozen evidence.** The paper starting balance is a
**Book/family-scoped configurable default, UI-editable**, sized for data-collection realism, frozen at
flip, never hand-adjusted, and **resettable only by a dated operator action**. Paper P&L never becomes
Treasury cash, never crosses the money boundary, and **never buys a seat**."*

**Verdict: LANDED IN FULL.** The rest of the memlog-104 package landed with it: DEC-0070 confirmed
(L387); standing evidence state (L388); one active paper target **per live binding** with plural demo
accounts acknowledged (L390 — rider 1); BENCHED = seat word only (L387, L481); decay in R with cohort
mismatch refusal (L394); return-to-live automatic only on clocked causes, operator signature for
anything touching real money (L393); typed close reason + whole-trade attribution to the opening bot
(AD-33 L368–369); broker-side protective stop wherever CT-18 declares support (AD-33 L366); demo/live
two-connection venue facts honored (L391, AD-28 L292 — rider 3).

---

### 13. Dead zone — BOTH kinds; absent for 24/7 calendars

**Ruling:** memlog 110 + 106 + 113 — DEAD ZONE = BOTH window kinds: the daily no-session band (~3h)
AND per-handover buffers (~45min); each a configurable window kind a Book enables; calendar-dependent;
absent for 24/7 crypto. Mechanism = hard pause on NEW entries; exits/safety/data never blocked.

**Landed where:** AD-38 L429 — *"**Three kinds ratified:** `news`; `daily_dead_zone` — the daily band
in which no session is meaningfully in the market; and `session_handover_buffer` — the pause around a
session handover. **Both dead-zone kinds exist and are different things** (operator ruling: the daily
no-session band and the per-handover pause are not one idea wearing two memories). Every kind is
**calendar-derived** … and is therefore **absent for 24/7 markets** — a calendar with no handover
produces no window."* A Book declares which kinds it enables (L428). Effect = new entries only,
never exits/protection/observation (L431). Widths non-authoritative (L430).

**Verdict: LANDED IN FULL** — the both-kinds ruling, the Book-enables mechanism, the 24/7 absence,
and the entries-only effect. See **Finding 3** on the ~3h citation's provenance.

---

### 14. Authority order + QMX-discussion barred for risk — does the spine cite accordingly?

**Ruling:** memlog 111(a) — *"AUTHORITY ORDER for risk/position-sizing/live-trading = GitBook +
trading-node documentation (archive/recovery + Documents/QMX wiki); **QMX-discussion's
risk/position-sizing system was REPLACED and is BARRED as a source there ('please don't')**; QML will
change with the system re-basing onto QMF."* Marked STANDING and "load-bearing for all remaining work."

**Landed where: NOWHERE.** A full-text search of the spine for `QMX-discussion`, `precedence`,
`barred`, `GitBook` (as a source-authority term) and `source authority` returns nothing on this
ruling. The `sources:` frontmatter (L12) lists `docs/…, tracker/map.md, .memlog.md` and no
precedence order at all.

**Aggravating:** the Inherited-invariants row at L34 is titled **"Authority order"** — but it carries
the *constitutional hierarchy* (bot → book → BMS → operator), a different ruling from the same
sitting. A reader (or the PRD/documentation-factory downstream) scanning for the operator's authority
ruling finds a row with the right name and the wrong content, and concludes it landed.

**Verdict: MISSING — see Finding 2 (material).** This is a standing source-precedence rule that binds
the PRD, the documentation factory, the backtesting sitting and the QML sitting. It is exactly the
class of ruling that dies silently in distillation because it governs *how to read*, not *what to
build*.

**Consequence already visible:** AD-38 L430 cites a number sourced from the barred layer without the
exemption on record — see **Finding 3**.

---

### 15. "The Book sets the bar" — `admission_bar` with not-yet-ruled blanks blocking live only

**Ruling:** memlog 108 — "Admission bar ('Book sets the bar') shape ratified: named unit-carrying
requirements, 'not yet ruled' allowed, blocks live money only." Seeded memlog 49.

**Landed where:** AD-32 L354–L357:
- L354: *"**`admission_bar` — 'the Book sets the bar':** an ordered set of named requirements, each carrying an opaque `measure_identity`…, a **mandatory unit**, a comparison (`at-least | at-most | within-band`), a threshold that is an exact rational **or the explicit literal `not yet ruled`** with its gap reference, and `evidence_requirements`…"*
- L355: *"**Blank blocks live money:** a Book whose bar holds any `not yet ruled` threshold registers and binds to non-live roles freely, and **binding to a `role = live` account is a `policy rejection`**. The container ships complete today with every number honestly blank."*
- L356 parity is structural; L357 no composite score / 0–100 rating / tier band.
- Renamed from banned `entrance_exam` (AD-30 L330; Conventions L524).
- Deferred L587: threshold values await the backtesting sitting, and block live binding until filled.

**Verdict: LANDED IN FULL**, including the exact three-part shape (unit-carrying / blank-allowed /
live-only block) and the anti-scoring guard.

---

### 16. Prediction linter + demo shakedown, NO performance probation

**Ruling:** memlog 108 — "**NO performance probation** (redemption loops stay dead) BUT a TECHNICAL
SHAKEDOWN precedes live: (a) LINTERS over the template config — completeness, units, worked-example
arithmetic recompute, plus operator's new **'prediction linter'** idea = static can-this-Book-register-
this-bot compatibility check; (b) demo/paper connection-and-execution shakedown; (c) one operator
signature on one assembled page."

**Landed where:** AD-32 L350–L353:
- L350: *"a new Book or BMS proves itself in three layers, and **no trial period, probation window, or paper-performance gate exists** (redemption loops stay dead)."*
- L351 Layer 1: completeness, a unit on every parameter, exact rationals, resolvability, *"**worked-example arithmetic recomputed** from the template's own declared numbers and refused on mismatch; and the **prediction linter** — a static compatibility check answering 'can this Book register this bot' before either is bound."*
- L352 Layer 2: *"On a demo/paper binding: connect, register a bot, execute. It proves the Book and its BMS can actually work, and **proves nothing about edge**."*
- L353 Layer 3: one operator signature on one assembled page (AD-18 card, plain-words summary an identity field). *"One packet, signed once."*
- L357: same three layers apply verbatim to a BMS.
- AD-30 L331 requires a `worked_example` in every Book definition; AD-18 L175 records the risk-binding landing.

**Verdict: LANDED IN FULL** — including the operator's own new idea (prediction linter), named as such.
**One micro-directive dropped — see Finding 6:** memlog 108(c) instructed "distill **cites** it" for
the corpus's own new-Book/BMS validation treatment ("validation like a bot — similar but not so
similar", archive/recovery + Documents/QMX). AD-32 carries no such citation.

---

### 17. Journals deepening — Book/BMS/bot journals as data-collection points

**Ruling:** memlog 107(2) — *"OPERATOR DEEPENING: the 'logbook' = the JOURNALS — Book journal, BMS
journal, per-bot journals are **the data-collection points**, defined in Documents/QMX — **'dig
deeper, it's not as simple as you think'** — distill must bind per-entity journal **streams** (paper
AND live worlds separated) onto AD-21 machinery from the old-wiki journal contracts."*

**Landed where:** AD-31 L339–L342:
- L339: *"Journal **streams stay writer-scoped** (AD-21…). The **Book journal, BMS journal, and per-bot journal — the operator's logbook — are declared read-time projections** over those streams, selected by entity identity. **An entity is not a writer, and no entity mints a stream of its own.**"*
- L340 (the load-bearing guarantee): *"Projections are derivable because **every risk-domain journal event and every risk record carries, as identity fields**: the Book-definition fingerprint, the binding identity (AD-29), and — where the act concerns one bot — the Bot identity plus its seat binding."*
- L341: *"**Paper and live are separated by construction:** a projection resolves inside one role-scoped namespace (AD-12). A projection spanning roles exists only as the explicitly-declared cross-role read of AD-35, never as a silent union."*
- L342: the legacy five Records streams survive as projection names only, mapped onto AD-21's seven types by one versioned mapping table in CT-25 — no second event catalog.
- AD-21 L193 carries the reciprocal clause: entity journals are read-time projections "never additional writers".

**Judgment asked for by this pass — honors or violates?**

**It honors the operator's substance and substitutes his mechanism, and the substitution is sound but
undisclosed.** The three journals exist, are named as the logbook, are paper/live separated, and are
bound to AD-21 and to the old-wiki Records contracts — all four things the operator asked for. The
substitution (projection, not entity-owned stream) is forced by AD-21's one-writer-per-stream law and
by the corpus fact recorded at memlog 117 that no per-bot streams exist; letting a Book "own" a stream
would require a Book to hold a `WriterId`, which AD-15/AD-8 forbid for a non-component.

**Two things keep it from being a clean pass:**

1. **The spine states the projection rule flatly**, as though it were the operator's own words. There
   is no line saying "the operator asked for per-entity streams; the corpus has none and AD-21 forbids
   entity writers, so the same guarantee is delivered as a projection." A later reader cannot tell a
   ruling from a distiller's correction.
2. **The collection guarantee at L340 is scoped to "every risk-domain journal event and every risk
   record."** It does **not** reach AD-27/CT-20 **venue observations** (order, fill, outcome), which
   are written under the adapter's `WriterId` on the `(VenueId, account)` stream and carry the command
   identity, the session epoch and the caller's ordinal — **not** a Bot identity. A *per-bot* journal
   therefore reconstructs fills only by joining through the exit record (AD-41 L475, which carries fill
   references and bot-scoped identity) or through the binding resolved into command identity (AD-35
   L391). That join is real and derivable, but it is nowhere declared, and "data-collection point" is
   precisely the phrase that should not depend on an undeclared join.

**Verdict: HONORS with a mechanism substitution — FLAGGED FOR OPERATOR (Finding 4).** Recommended
fix is two sentences, not a redesign: (a) a disclosure line in AD-31 naming the substitution and its
reason; (b) either extend L340's identity-field mandate to CT-20 observations produced under a binding,
or declare the join path explicitly so the per-bot journal is provably reconstructible.

---

### 18. QML non-foreclosure

**Ruling:** memlog 105 + 109 — "nothing in this sitting may foreclose QML's uniformity mechanism";
reusable donor assets identified (ExitLogicRef, CloseReason taxonomy, template-grammar vs per-instance-
values split); reconciliation = its own sitting (GAP-0047).

**Landed where:**
- Deferred L591: *"QML reconciliation onto QMF (GAP-0047) | Own sitting; `qml-original-dig.md` records the donor assets (ExitLogicRef, CloseReason, template-grammar split) already consumed by AD-33 — **nothing in this sitting forecloses QML's uniformity mechanism**."*
- Donors actually consumed: `ExitLogicRef = {module_id, config}` at AD-33 L367 with the QML citation, and again at AD-40 L461 (per-family full-loss-price derivation); the `CloseReason` taxonomy generalized at AD-33 L368; template-grammar vs per-instance values at AD-30 L326.
- Companion listed in frontmatter L13.
- Nothing in AD-29..AD-41 constrains bot anatomy: AD-17's multiplicity invariant is untouched, AD-32 explicitly proves "nothing about edge" (L352), and AD-33 permits a Book to declare **zero** bot-intent kinds (L367).

**Verdict: LANDED IN FULL** — non-foreclosure stated, donors credited, sitting deferred.

---

## Part B — Five-hats risk docket (16 items)

| Item | Ask (five-hats-sweep.md) | Landed where | Verdict |
|---|---|---|---|
| **A-1** | "Comparable" needs a definition beyond `world = live` | AD-35 L394 cohort rule — `cohort_key` = Bot identity, Book identity + template version, pinned canonical sensing feed, configured producers' fingerprints, calendar identity + version, instrument identity or declared equivalence, active-control set; **account role deliberately allowed to differ**; mismatch = `policy rejection`. Cross-role read explicitly permitted L395 | **Landed** |
| **A-2** | No package owns a performance result | AD-41 L482 mints **CT-32 performance-result container** in `qmf-risk` (binds L472); AD-16 L163 registers the kind | **Landed** |
| **A-3** | Two identically-labelled reports can hold different numbers | AD-41 L483 — a metric is a governed AD-23 producer, arithmetic pinned by **its own contract format version**, change = a mint with before/after evidence; AD-32 L356 parity-is-structural refusal; AD-12 L136 producer contract identity | **Landed** |
| **A-5** | Multi-currency aggregation unruled, two hats need it | AD-40 L463 USD numeraire + non-USD `policy rejection` + seam ships; L468 cross-venue aggregation needs an operator-declared equivalence record; Deferred L589 | **Landed** |
| **A-7** | Suppressed actions are the highest-value analytic dataset | AD-36 L407 suppression first-class (suppressing + suppressed authority, reason class, **would-have-been action by fingerprint**, scope, arbitration fingerprint); AD-21 L193 `suppressed` subtype; AD-41 L482 **suppression accounting** in CT-32 "so gates never read as decay"; AD-38 L431 blocked-decision journaling on the veto path | **Landed — best-served docket item** |
| **A-8** | Exit ownership decides P&L attribution; the ruling should say so | AD-33 L369 whole-trade attribution to the opening Bot, in R, no counterfactual, no apportionment; reports partition by close reason | **Landed** |
| **P-2** | Book charter needs a declared numéraire | AD-30 L331 `accounting_currency` declared per Book; AD-40 L463 | **Landed** |
| **P-3** | Correlation ledger falls between framework and node | AD-31 L344 — **cohort-correlation evidence** = declared CT-23 input shape with stated as-of knowledge time, computed outside `qmf-risk`, **enforced node-side**, threshold unratified; renamed apart from fill-attribution label and `correlation_id` | **Landed** |
| **P-4** | Book-to-account cardinality across venues | AD-29 L305 **an instance never spans venues**; L304 risk domain = the binding; L306 several Books on one account named | **Landed** |
| **P-6** | Verify the day-boundary seam fits prop-firm rules without modeling a firm | AD-8 L100 account-scoped day-boundary calendar (pre-existing socket); Deferred L590 — *"AD-8's account-scoped day-boundary calendar plus AD-40's baseline/derivation discipline hold the socket; no firm is modeled in V1"* | **Landed as verified-socket** |
| **P-7** | Exposure limits need a unit surviving new asset classes | AD-40 L468 — limits **only in R or notional in the Book's numeraire**; a lots-denominated limit is a `policy rejection` at template validation, citing DEC-0015 | **Landed** |
| **T-1** | Kill switch is node territory with no named seam | AD-36 L403 mints **CT-30 control-action contract** (typed kind, authority + kind, subject scope, reason class, evidence refs, refusal semantics, evidence record; fan-out = AD-27 compound command) | **Landed** |
| **T-4** | Same-tick priority cannot be written before venue capabilities are known | AD-37 L420 scope resolution reads CT-18 `netting | hedging` **before** dispatch; AD-29 L307 bind-time capability check (`unsupported capability` at bind time, never trade time); AD-28 L288 protection primitives in the CT-18 roster | **Landed — sequencing hazard closed** |
| **T-6** | Blackout behavior for already-open positions | AD-38 L437 — whether a window closes open positions is a Book declaration entering AD-37 at **rank 2** as `window_forced_flat`, *"a ranked rung, never a bypass and never a separate code path; **declaring none is the V1 posture**"*; L431 a window never blocks an exit | **Landed** |
| **X-5** | One Book spanning venues vs deterministic same-tick priority | AD-29 L305 (instance never spans venues) + AD-37 L415 (priority per `(VenueId, account)` stream, cross-stream a **declared non-guarantee**) — the conflict is dissolved, not traded off | **Landed** |
| **X-6** | Paper comparable to live vs paper running through blackouts | Resolved by operator override (memlog 97): AD-38 L431 + AD-35 L389 stop paper entries, recording continues; comparability preserved via AD-35 L394 cohort rule with the **active-control set** in `cohort_key` and AD-36 L407 typed edge from evidence to the controlling record | **Landed** (see note below) |

*Note on X-6:* memlog 97 records that the operator's ruling *"Overrides the earlier keep-paper-flowing
lead and five-hats X-6 tag-and-run shape."* The spine lands the ruling but does not record that X-6's
tag-and-run shape was overridden, while Deferred L580 keeps the full five-hats sweep alive as "input
register for every remaining sitting." A later sitting re-reading X-6 could take the superseded shape
as live. One clause in the Deferred row would close it. Low severity — recorded as **Finding 10**.

**Docket verdict: 16 of 16 landed. None deferred, none dropped.**

---

## Part C — Memlog sweep, entries 84–117 (items not covered above)

| Entry | Ruling / direction | Landed where | Verdict |
|---|---|---|---|
| 84 | GAP-0035 / AD-26 secret lifecycle — references not values, injected at root, never in repos/logs/evidence/fingerprints, unavailable-dependency refusal carrying the reference, CM owns OAuth refresh, store-before-discard, compromise drill = cTID re-auth, demo-credentials-only, UI = platform | AD-26 L260–265 in full, incl. the UI rider (L265 "Credential entry and management UI is platform territory") | Landed |
| 85–88 | GAP-0036/0038 (AD-27/AD-28) | Pre-existing, re-verified: five-command amendment L273, protection capability fields L288, verification-suite refusal clause L293 | Landed |
| 91 | Risk sitting scope + carried-in items (dead-zone idea, flatten authority leftover, SQS open) | Dead zone AD-38 L429; flatten authority AD-36 L404 with AD-27 L278 now pointing to it; SQS AD-39 | All three closed |
| 92 | DEC-0095 — BMS versioned rulebook, GitBook shape = default v1 template, one BMS at a time, one version many Books, **variants = new versions never stacking** | AD-29 L302–303 (superseded/refined by entry 101); default-v1 framing at L303; **variants clause absent** | Landed except the variants clause — **Finding 5** |
| 93 | Meta-model: defaults + versions + copies; templates declare configurable vs non-configurable; adding an account offers a copy; hard rules bind figures/ranges, never what the operator may build | AD-30 L325–326 for the first three. The last is carried by the pre-existing don't-box-in row (L31) plus AD-32 L352 ("proves nothing about edge") and AD-33 L367 (a Book may declare zero bot-intent kinds) | Landed |
| 94 | Book-to-venue: one binding per account; another account gets its own BMS copy + own connection; cross-broker aggregation = after-the-fact report with stated as-of time | AD-29 L304–305 — *"Cross-binding and cross-broker figures are after-the-fact reports at a stated as-of knowledge time, carrying lineage; **they never gate an order**"* | Landed |
| 96 | amend_order/dynamic SL-TP deferred pending primary-doc study | Superseded by entry 110; AD-34 | Closed |
| 97 | News ruling + multi-pair wrinkle | AD-38 L431, L433 | Landed (Finding 8) |
| 98 | Kill switch / kill line / flatten authority | AD-36 L402–405 | Landed |
| 99 | Stop-out + bench counter | AD-41 L476–479 — **the "what counts" half diverges: Finding 1** | Partially landed |
| 100 | (1) chain correction; (2) version ≠ copy; (3) QML dig; (4) node material to tracker | (1) AD-29; (2) AD-30 L326; (3) Deferred L591; (4) node-ledger, outside spine | Landed |
| 101 | DEC-0095 refined — account-facing BMS, final cardinalities, verbatim authority split + migration caveat, risk domain = the BMS instance's account, X-5 resolved | AD-29 L301–306 | Landed in full |
| 102 | GAP-0043 SQS V1 — ratio sensor, per-class hard-block threshold, hysteresis band, 4-sigma outlier guard, conservative sentinel (undefined ⇒ block), four-layer authority boundary (SQS computes, MIS transports, Book door decides; unreachable = hard block), all variables configurable exact rationals, versioned v2 with depth | AD-39 L445–452 — every clause, incl. the legacy `-1.0` sentinel converted to a typed marker (L445), the fingerprinted baseline artifact (L447), recorded-but-non-authoritative corpus numbers (L449), and blocks-only-never-shrinks keeping the score off the money path (L451) | Landed in full |
| 103 | Configurable = UI-editable | Part A.1 | Landed in full |
| 104 | Paper package + three riders | Part A.12 | Landed in full |
| 105 | QML direction | Part A.18 | Landed |
| 106 | Dead-zone mechanism ratified, width open | AD-38 L429–430 | Landed |
| 107 | Books package — inline identity-bearing numbers with config-template semantics, ui-editable per variable, UI edits mint versions; two-status split, status = read-time fold; **journals deepening**; git-logic versioning | AD-30 L325–329 (all four version-graph properties: append-only graph, supersedes-as-commits, derivable diffs, every old version readable forever); AD-30 L327 inverts the legacy registry-pointer rule; AD-35 L387/L388 + AD-41 L481 two-status split; Conventions L526 fold-not-field; **journals — Finding 4** | Landed except journals disclosure |
| 108 | Validation amended — no probation, linters incl. prediction linter, shakedown, one signature, admission bar shape; **distill cites the corpus treatment** | AD-32 L350–357; citation **absent — Finding 6** | Landed except the citation |
| 109 | QML dig — role survived, uniform machinery dropped, reusable donors | AD-33 L367–368, AD-40 L461, Deferred L591 | Landed |
| 110 | Round 5 — dead zone both kinds; amend command minted; V1 = breakeven ratchet only | AD-38 L429; AD-34 L376–380; AD-27 L273 | Landed in full |
| 111 | Standing corrections (a) source-authority order + QMX-discussion barred; (b) USD numeraire; (c) close news from corpus; (d) close priority/declared-loss/B-split from corpus with citations, **mark genuinely-new pieces explicitly**; (e) don't re-discuss node internals | (a) **MISSING — Finding 2**; (b) AD-40 L463 landed; (c) AD-38 landed; (d) partially — numbers are marked non-authoritative (L430, L449, L479) but structural inventions are not — **Finding 7**; (e) outside spine | Two of five weakened |
| 113 | GAP-0042 corpus closure — one window contract; two-instants-not-offsets; fail-closed on refresh failure; widen-never-shrink incl. revisions, forward-only, older-revision decisions stand and are tagged; currency→instrument re-mechanised as declared exposure records, missing ⇒ blocked + data-quality journal; severity verbatim, no QMX scale, four-tier ladder not revived; multi-pair per instrument; open positions untouched by default; all numbers configurable with no spine value, ±15min withdrawn | AD-38 L428, L430–436 — every clause present; the dead four-tier ladder is correctly absent rather than mentioned | Landed in full |
| 114 | GAP-0046 / AD-37 — one arbitration point per stream; cross-stream non-guarantee; tier 1 venue-resident outside ordering + superseded-by-fill; tier 2 corpus-derived rank order (operator > protection > BMS/Book forced flats > fast invalidation > ordinary exits and amendments); ranks declared mandatory non-defaultable; collapse (rank decides attribution) + conflict (higher wins outright, lower never undoes higher); CT-18 netting/hedging before dispatch; hold-time + no-overnight unified at rank 2 with two trigger forms, no values | AD-37 L415–421 — every clause, ranks 0–4 in the ruled order | Landed in full (rationale trail not carried — Finding 7) |
| 115 | AD-40 declared full-loss price — mandatory before open, no price ⇒ no `original_risk_distance` ⇒ invalid-input refusal at admission; R's definition; **frozen at admission** incl. against the breakeven ratchet; per-family derivation via `ExitLogicRef`; resting stop is a separate CT-18/Book question; **consequence: a strategy with no planned loss point cannot trade in QMX** | AD-40 L459–L461 — all landed; the plain-words consequence sentence dropped (**Finding 9**) | Landed |
| 116 | B-coupling split — two typed variables, optional declared derivation as fingerprinted data visible in charter and consuming artifacts, unit-kind checker enforces, FORM-0004 superseded as mis-named rate, FORM-0006 dead by name and retained as permanent negative test, old coupling recorded as the motivating defect | AD-40 L465–467 — every clause, incl. "the defect that motivated the mandate" and the permanent negative test | Landed in full |
| 117 | Distill manifest — 13 ADs + cross-AD amendments | AD-27 five commands L273 ✓; AD-28 protection fields L288 + refusal clause L293 ✓; AD-21 suppressed subtype + entity-journal projection L193 ✓; AD-16 **nine** risk record kinds + `continues-as` edge L163 ✓ (Book definition, BMS definition, Book binding, binding transition, exit record, control action, control window, performance result, currency-exposure = 9); Inherited rows L34–35 ✓; Conventions naming splits + fold-not-field L524/L526 ✓; dependency section "risk sitting requests no edge" L504 ✓; Deferred rewritten — GAP-0039..0046 rows gone, ten new rows present ✓; frontmatter scope GAP-0001..0046, status draft, binds CT-22..CT-32, six briefs + QML dig + SLTP research in companions ✓ | Manifest fully executed |

---

## Part D — Findings

### Finding 1 — MATERIAL — Bench counter's "what counts" half was quietly broadened

**Ruling (memlog 99):** *"the counter counts **STOP-OUTS = exits at ~full planned loss** ('we only
count losses at negative 1R, I think'); threshold is PER-BOT … and emphatically CONFIGURABLE."*

**What the spine says:** AD-41 L476 keeps the operator's definition — *"A stop-out is a typed risk
event: **an exit at approximately the full planned loss**"* — and then L477 makes the bench counter
count something else: *"The counter counts **qualifying loss exits** — closes whose `realized_r` is
**strictly negative** after costs. … **Any magnitude threshold finer than the sign stays unratified.**"*
Conventions L524 completes the decoupling: `qualifying_loss_exit` is "the bench's input", and the word
"stop-out" is banned bare.

**How it weakens:** under the operator's ruling a −0.15R scratch does not move the bench counter;
under the spine it does. With a scalper threshold of 2, two small scratches bench the bot. The
operator ruled *breakevens* out and *−1R-class losses* in; the spine ruled *breakevens* out and
*everything below zero* in. The breakeven half (Part A.5) is faithful; the counting half is not.

**Why it happened, and why it is defensible:** the brief (`brief-formulas-stopout.md` §F-8) recommended
sign-only precisely because "approximately full loss" needs a number and AD-13 forbids inventing one;
the operator's own recall was hedged ("I think"). The spine discloses the choice ("any magnitude
threshold finer than the sign stays unratified"). What it does **not** disclose is that this differs
from what the operator said.

**Fix (one of):** (a) put the predicate on the Book template as a declared, UI-editable, unit-carrying
variable with **no QMF default** — the do-not-default idiom this spine already uses for AD-37 ranks and
AD-27 deadlines — so the operator's "~1R" becomes a configuration he sets rather than a number the
spine invents; or (b) keep sign-only and add one clause recording that the operator's stated predicate
was full-loss-class, that no threshold is ratifiable without measurement, and that AD-41's breakeven
metric is the evidence that will settle it. Option (a) is more faithful and costs nothing.

**Put to the operator.**

---

### Finding 2 — MATERIAL — The source-authority order for risk is missing from the spine

**Ruling (memlog 111a, marked STANDING and "load-bearing for all remaining work"):** *"AUTHORITY ORDER
for risk/position-sizing/live-trading = GitBook + trading-node documentation (archive/recovery +
Documents/QMX wiki); QMX-discussion's risk/position-sizing system was REPLACED and is **BARRED** as a
source there ('please don't')."*

**What the spine says:** nothing. No precedence statement anywhere; `sources:` (L12) lists paths with
no order; no "barred" clause; no mention of QMX-discussion.

**How it weakens:** this rule governs *how every downstream artifact reads the corpus* — the PRD, the
documentation factory, the backtesting sitting, the QML sitting and the Bot-schema sitting all inherit
the spine, not the memlog. Without it, a future agent grounding a risk or position-sizing claim in
QMX-discussion is doing exactly what the operator forbade, and the spine gives it no reason to stop.

**Aggravating factor:** the Inherited-invariants table already has a row titled **"Authority order"**
(L34) carrying the *constitutional hierarchy*. Two distinct rulings from the same sitting share a name,
and the one that landed makes the one that did not look landed. This is the exact failure mode this
review exists to catch.

**Fix:** a new Inherited-invariants row, distinctly named so it cannot be confused with L34 — e.g.
*"Corpus precedence for risk / position sizing / live trading: GitBook + trading-node documentation
(archive/recovery, Documents/QMX wiki) are authoritative; QMX-discussion's risk and position-sizing
system was replaced and is barred as a source there | Operator ruling 2026-08-20 | AD-33, AD-37, AD-38,
AD-40, AD-41; every downstream sitting"* — plus a precedence line in the `sources:` frontmatter.

---

### Finding 3 — MEDIUM — AD-38 cites a barred-layer number without the exemption on record

**What the spine says:** AD-38 L430 — *"a ~3h daily no-session band (**oldest corpus**)."*

**What the memlog says (113):** the ~3h band comes from **QMX-discussion Flow 9**, *"cited for the
DEFINITION only, non-risk structure, permitted under the round-5 authority bar."*

**How it weakens:** the one citation in the risk increment that needs the barred-source exemption is
the one whose source is anonymised to "oldest corpus", and the exemption reasoning is not recorded.
Combined with Finding 2 (the bar itself is missing), the spine cannot demonstrate compliance with a
standing operator ruling at the single place it matters. The number is correctly marked
non-authoritative, so no invented value entered the spine — this is a traceability defect, not a
numeric one.

**Fix:** name the source and carry the one-clause exemption: *"~3h daily no-session band (QMX-discussion
Flow 9 — cited for the definition only; that layer is barred as a risk/position-sizing source per the
corpus-precedence rule, and no risk or sizing content is taken from it)."*

---

### Finding 4 — MEDIUM — Entity journals: sound substitution, undisclosed, with an unstated join

Full analysis at **Part A.17**. Summary:

- **Substance honored:** the three journals are named as the operator's logbook, paper/live separated
  by role-scoped namespace, bound to AD-21's seven types and to the legacy five Records streams
  through a versioned CT-25 mapping table.
- **Mechanism substituted:** the operator said per-entity *streams*; the spine rules them read-time
  *projections* and states flatly that "an entity is not a writer, and no entity mints a stream of its
  own" (L339). The substitution is forced by AD-21/AD-15 and by the corpus having no per-bot streams —
  but the spine does not say so, so the correction is invisible.
- **Collection guarantee under-scoped:** L340's mandatory identity fields cover risk-domain journal
  events and risk records only. AD-27/CT-20 venue observations (order, fill, outcome) carry command
  identity, session epoch and caller ordinal — no Bot identity. A per-bot journal therefore depends on
  an **undeclared join** through the exit record (L475) or the intent-resolved binding (L391).

**Fix:** (a) one disclosure sentence in AD-31 naming the substitution and its reason; (b) either extend
L340's mandate to CT-20 observations produced under a binding, or declare the join path so the per-bot
journal is provably reconstructible.

**Flagged for the operator** — he called this one out specifically ("dig deeper, it's not as simple as
you think"), so the substitution should be his to accept, not the distiller's to make silently.

---

### Finding 5 — LOW — "Variants are new BMS versions, never simultaneous stacking" is implicit only

**Ruling (memlog 92):** *"crypto/prop-firm variants = NEW BMS versions, never simultaneous stacking."*

**What the spine says:** AD-29 L302 forecloses stacking structurally ("a Book binds exactly one BMS at
a time"); AD-30's version graph makes any variant a version; Deferred L590 refers to "a prop BMS
variant". No clause states the rule.

**How it weakens:** low. The mechanism holds; only the *stated intent* is missing, which matters when
the prop-firm or crypto extension is designed and someone asks whether a second BMS may ride alongside.

**Fix:** append to AD-29 L302: *"A crypto or prop-firm BMS is a new BMS version, never a second BMS
stacked beside an existing one."*

---

### Finding 6 — LOW — AD-32 drops an explicit citation directive

**Directive (memlog 108c):** *"Trading-node treatment of new-Book/BMS validation exists in
archive/recovery + Documents/QMX ('validation like a bot — similar but not so similar') — **distill
cites it**."*

**What the spine says:** AD-32 (L346–357) carries no citation to the corpus treatment.

**Fix:** one parenthetical in AD-32's opening line noting that the corpus treats new-Book/BMS
validation "like a bot — similar but not so similar" (archive/recovery + Documents/QMX), which is why
the three layers are technical rather than performance-based.

---

### Finding 7 — LOW — "Mark genuinely-new pieces explicitly" only half honored

**Directive (memlog 111d):** close same-tick priority, declared full-loss price and B-coupling from
corpus **with citations**, and **mark genuinely-new pieces explicitly**.

**What the spine does:** marks *numbers* consistently ("Recorded corpus evidence, non-authoritative" —
L430, L449, L479) and cites corpus grounding for AD-40's declared-loss rule (L461) and the B defect
(L467). It does **not** mark *structural* inventions: AD-37's collapse and conflict rules (L418–419)
and the unified force-flat rule (L421) read as derived, though memlog 114 records hold-time force-flat
as existing in the corpus **as a name only, with no value**, and the collapse/conflict pair as this
sitting's own construction.

**Fix:** a short "corpus-derived vs newly minted" marker on AD-37's two rules and the force-flat
unification — one clause each.

---

### Finding 8 — LOW — News effect narrowed from "all trading" to "new entries", narrowing undisclosed

**Ruling (memlog 97):** *"stops **ALL trading** on that instrument — live AND paper, no exceptions."*

**What the spine says:** AD-38 L431 — *"a window blocks **new entries** on the instruments in scope,
**and nothing else**. It never blocks an exit, a protection amendment, a protection action, or
observation."*

**Assessment:** the narrowing is correct engineering (blocking exits would trap risk, which AD-38's own
"Prevents" line names), corpus-grounded via CT-BMS-04, and consistent with AD-38 L437 routing any
window-driven close through AD-37 rank 2 as a declared Book rule. The live-AND-paper half — the part
the operator was emphatic about — landed exactly. Only the record of the narrowing is missing.

**Fix:** one clause: *"The operator's ruling was stated as 'stops all trading'; it is implemented as
entries-only because blocking exits would trap risk behind the very window meant to reduce it — a
window that closes positions is a declared Book rule at AD-37 rank 2, never an implicit effect."*

---

### Finding 9 — LOW — AD-40's plain-words consequence sentence dropped

**Ruling (memlog 115):** *"**Consequence stated:** a strategy that deliberately runs with no planned
loss point cannot trade in QMX."*

**What the spine says:** AD-40 L461 delivers the rule (no declared price ⇒ no `original_risk_distance`
⇒ `invalid input` at admission) but not the consequence in plain words. The operator is non-technical
and the ruling explicitly asked for the consequence to be stated.

**Fix:** append the sentence to L461 verbatim.

---

### Finding 10 — LOW — X-6's superseded shape is not marked superseded

**Ruling (memlog 97):** the news ruling *"Overrides the earlier keep-paper-flowing lead and five-hats
X-6 tag-and-run shape."*

**What the spine says:** the ruling landed (AD-38 L431, AD-35 L389), but Deferred L580 keeps the whole
five-hats sweep as a live "input register for every remaining sitting" with no supersession note, so a
later sitting can re-read X-6's tag-and-run shape as an open option.

**Fix:** append to L580: *"— items closed or overridden by a later ruling are marked in the memlog;
X-6's tag-and-run shape is superseded by the 2026-08-20 news ruling."*

---

## Part E — Items to put to the operator

1. **Finding 1 (bench predicate).** "You said the counter counts full-loss exits — about −1R. The
   spine currently counts **any** losing exit, however small, because no −1R-ish threshold has been
   measured. Do you want the predicate to become a Book variable you set (recommended), or should the
   spine keep counting every loss until measurement settles it?"
2. **Finding 4 (entity journals).** "You said the Book, BMS and per-bot journals are the
   data-collection points. The spine makes them **views** assembled from the component journals rather
   than three journals of their own, because a Book isn't a thing that writes. The information is all
   there and separated paper-from-live — but fills currently reach the per-bot view through a join the
   spine doesn't spell out. Confirm the views-not-streams reading, and we will pin the join."
3. **Finding 2 (corpus precedence)** needs no operator input — it is a recorded ruling that simply has
   to be written into the spine — but the operator should be told it was missing, since he flagged it
   as standing.

---

## Companion coverage

All six risk briefs and both risk-sitting research companions are declared in the spine frontmatter
(L13) and their delegated (non-operator-question) proposals traced above:
`brief-book-bms.md` (Items 1–8, incl. the delegate-quality contract mapping → AD-16 L163),
`brief-exit-ownership.md` (E-1..E-5 → AD-33, AD-34, AD-40), `brief-formulas-stopout.md`
(F-1..F-13, §15 delegated set F-2/F-4/F-6/F-7/F-11/F-12/F-13 → AD-40, AD-41 — F-8 is Finding 1),
`brief-news-sqs.md` (NEWS-1..10, SQS-1..5 → AD-38, AD-39), `brief-paper-mode.md`
(PM-1..PM-9 → AD-35, AD-41), `brief-priority-killswitch.md` (PK-1..PK-11 → AD-36, AD-37, AD-33 L366,
Deferred L590). **No delegated brief proposal was found dropped.**
