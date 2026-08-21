---
brief: news-sqs
sitting: risk (GAP-0039..0046)
cluster: GAP-0042 news control · GAP-0043 SQS
five-hats items carried: T-5 (news revision at decision time), T-6 (open-position behavior needs a rank, not a path), A-7 (suppressed actions), X-6 (paper evidence under an active control)
status: synthesis-lead recommendation — nothing here is ratified
date: 2026-08-20
---

# Decision brief — news control (GAP-0042) and SQS (GAP-0043)

## How precedence was applied

One order was used everywhere below, highest first:

1. **Current rulings** — `docs/` + `tracker/` on Desktop/QMX, the ratified spine AD-1..28, and dated operator rulings (2026-08-17 recovery addendum, 2026-08-19 framework-vs-node, 2026-08-20 clarifications).
2. **Old wiki** — `Documents/QMX/wiki/`, 2026-07-18..27, incl. the old project spine/PRD/epics and the old node build's ratified standards.
3. **GitBook** — the 2026-07-18 capture and the live site (changelog unchanged since 2026-07-08; the two capture dirs are byte-identical).
4. **QMX-discussion** — the oldest bot-centric vault (~2026-04/05), whose "Canonical v1.0" self-labels are voided by every later layer.

Two standing filters were applied on top: **no invented numbers** (AD-13; `docs/components/qmf-risk.md:110` FM-6 — "No formula or transition may be invented"), and the **framework-vs-node split of 2026-08-19** — news windows and kill-switch runtime are node territory, QMF carries only contracts and seams.

One correction to a premise before anything else: the five-hats sweep records the ±15-minute pair-scoped window as "**ratified in shape and unratified in number**" (T-5). The current registry says something stricter — `news_blackout_before` / `news_blackout_after` are `value: null`, `units: minutes`, `gap: GAP-0042`, with the note "**Fifteen minutes was tentative and is not a live value**" (`docs/registry/variables.yaml:438-460`, DEC-0072). Fifteen is not a number to be confirmed; it is a number that was withdrawn. Nothing below proposes a replacement.

---

# Part A — GAP-0042, news control

`GAP(GAP-0042): Define pair-scoped news windows, severities, mappings, open-position behavior, and overrides.` (`docs/components/qmf-risk.md:77`). Five sub-questions, taken one at a time, plus three the gap text does not name but the evidence forces.

---

## NEWS-1 — What QMF carries: one control-window contract, not a news feature

### (1) Evidence

**Current.** ADR-0010 keeps only the scoping fact: "News controls remain pair-scoped" (`docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:31`, DEC-0072); `docs/contracts/ct-25-risk-journal.yaml:17` restates "News blocking is pair-scoped and distinct from SQS". No news contract exists in the current corpus — CT-22/CT-24 are null placeholders. The spine already carries the two halves QMF needs: AD-21 ratifies that "the **news-calendar recorder** keeps provider-native identity and revisions" and that every external fact carries "event-time, known-at, **source**, and revision" (AD-19; spine:191, :179); AD-25 draws the line explicitly — "Observing a news instant or release as evidence is ordinary input consumption, bound to the revision known at observed-at; **acting on news stays node territory**" (spine:244). AD-28 declares the protection primitives the node will actually use — `suspend-new | drain | close_all` — as CT-18 capability surface (spine:286), and AD-27 states that "`suspend-new` takes local effect instantly with no venue round-trip" (spine:273).

**Old wiki / old spine.** CT-BMS-04 News Block Directive, fields verbatim: `directive_id, affected_currency, affected_pairs[], window_start_utc, window_end_utc, reason` (`contracts/ct-bms-04-news-block-directive.md:24-30`). Ownership: "BMS Exposure owns calendar import and compilation" (`:36`). The old spine put the same thing at AD-22 (`ARCHITECTURE-SPINE.md:204`, old project).

**GitBook.** Identical CT-BMS-04 schema, one rule: "Directive applies to live and paper books." Emitter is the BMS Exposure desk → KSA (`components/book-management-system.md:36`).

**Oldest layer.** No directive object; news lived as MIS snapshot fields `news_kill_active / news_kill_level / news_kill_symbols / news_kill_expires_utc` (`02-Components/04-market-intelligence-service.md:266-269`) — a mutable runtime flag, not a record.

Precedence result: the *record* shape is stable across three layers and survives; the *owner* (BMS Exposure desk) is a node-side organ under the 2026-08-19 split and does not survive as a QMF component.

### (2) Bucketing — **both**

**Re-buckets to node:** the calendar import ritual, the compilation of events into windows, the decision that a window blocks anything, and the enforcement path (`suspend-new` at the adapter).

**Stays QMF, as one seam:** a **control-window record** — a typed, fingerprinted, append-only evidence record with (a) the AD-21 external-fact quadruple `(source, source-native event id, revision, known-at)`, (b) the window as two instants (AD-8 int64 UTC ns), (c) a **declared scope** as an explicit set of instrument identities plus the currency that generated it, (d) a reason class, and (e) a format version. It is a *window*, not a *news window*: the dead zone (NEWS-9) and any future scheduled no-trade band reuse it rather than minting a second mechanism.

Note this is deliberately **not** CT-BMS-04: `affected_currency` as an authoritative field cannot survive AD-9 (see NEWS-2), and "directive" implies an instruction, whereas QMF must hold evidence and let the node instruct.

### (3) Recommended ruling

Mint one control-window contract in `qmf-risk` (declared shape only, no behavior), carrying provider-native identity + revision, absolute instants, a resolved instrument scope, and a reason class. Every window is evidence; nothing in QMF acts on one.

Alternatives weighed. *(a) Keep CT-BMS-04 as-is* — rejected: it carries `affected_currency` as authoritative and `affected_pairs[]` as "a non-authoritative hint" (`ct-bms-04:36`), which forces the consumer to derive pairs from a currency string, and AD-9 forbids the only cheap way to do that. *(b) Put the whole thing in the node and have QMF carry nothing* — rejected: the news calendar is external evidence with revisions, and AD-19/AD-21 already oblige QMF to store external facts with source and revision; a node-private window would be un-replayable, and T-5's reproducibility requirement dies. *(c) Make it a news-specific contract* — rejected in favour of the generic window, because the operator already has a second window (the dead zone) with identical mechanics and a different cause.

### (4) What would change it

If the operator rules that news blocking must be able to *close* positions (NEWS-5 = "close-before"), the record needs an effect-class field and the node's enforcement becomes a ranked rung in the same-tick order — the record shape still holds, but the risk sitting must then write the priority rank in the same pass.

---

## NEWS-2 — Currency → instrument mapping collides head-on with AD-9

**This is the sharpest finding in the cluster.**

### (1) Evidence

**Old wiki, verbatim:** "Compilation maps `affected_currency` to **every pair containing that currency**; `affected_pairs[]` is a non-authoritative hint" (`contracts/ct-bms-04-news-block-directive.md:36`). Old spine AD-22, verbatim: "Compilation is **currency → ALL pairs containing that currency** … Door 7 blocks on `affected_currency` **membership of the intent's pair**" (`ARCHITECTURE-SPINE.md:204`, old project). Oldest layer: "The News Scope Resolver maintains a currency-impact map: a news event tagged as affecting USD **blocks all USD-denominated pairs**" (`02-Components/04-market-intelligence-service.md:322`).

**Current ruling that breaks it:** AD-9 — "instrument identity is (venue, venue's own symbol), **the symbol opaque and never parsed**" (spine:110). "Membership of the intent's pair" is symbol parsing. Every layer's mapping rule is executed by reading `"USD"` out of `"EURUSD"`, and that operation is now prohibited framework-wide. The five-hats sweep reaches the same wall from the exposure side (P-1: "the fix must not be symbol parsing") and conflict X-2 states the resolution shape: a declared, dated, operator-minted record, "never an inference".

**What exists to build on:** AD-28 already requires adapter-produced "instrument/account metadata snapshots … recorded by the root — AD-22's typed configuration inputs — with full-metadata prerequisites declared (a light symbol list is insufficient where scaling metadata lives only on the full record)" (spine:287), and CT-18 owns an "instrument-metadata surface" (spine:286).

Precedence result: current ruling wins outright. The mapping rule survives *in intent* — one currency's event touches every instrument exposed to that currency — and dies *in mechanism*.

### (2) Bucketing — **stays QMF (seam)**

QMF carries a **currency-exposure record** for an instrument: a dated registry record (AD-16 kind, fingerprinted, addable-never-redefined) declaring which currencies an instrument is exposed to. Populated from the venue's own instrument metadata where the venue declares it (AD-28's metadata surface), operator-declarable and operator-correctable where it does not, never derived from the symbol text. Window scope resolution then reads records, not strings — and the resolved instrument set is what the control-window record stores (NEWS-1).

The node still owns the compile step and the block.

### (3) Recommended ruling

Currency→instrument scope is resolved through declared per-instrument currency-exposure records. **Missing record ⇒ the instrument is treated as affected and blocked**, and the missing record is journaled as a `data quality` event.

Alternatives weighed. *(a) A single global currency→pair table* — rejected: with six venues the same economic instrument has six identities (AD-9), and one table would have to be keyed by a normalized symbol, i.e. parsing by another name. Per-instrument records make news scoping multi-venue-correct **without** depending on the operator-minted exposure-equivalence record five-hats P-1 asks the registry sitting for — the two are complementary, not sequential. *(b) Missing record ⇒ do not block* — rejected: it fails open on a safety control, contradicting the ratified "unknown high-impact coverage blocks conservatively" posture (`ct-bms-04:38`) and the spine's fail-closed default. *(c) Keep `affected_pairs[]` as the authoritative field and drop currency entirely* — rejected: the provider publishes a currency, not a broker's symbol list; dropping the currency loses the evidence link back to the event and makes revisions unmatched.

### (4) What would change it

If the venue sitting's CT-18 verification finds that cTrader-family metadata reliably declares base/quote currencies per symbol, the operator-declaration half becomes a fallback rather than a co-equal path, and the "missing record" case gets rare enough to consider a louder refusal instead of a silent conservative block. If a venue is added whose instruments are not currency-pairs (crypto perp, equity — both explicitly in scope for the nouns per DEC-0015), the record must already be a *set* of exposures, which is why it is specified as a set now.

---

## NEWS-3 — Window shape: absolute instants, not minute constants

### (1) Evidence

**Current:** both registry slots are `value: null`, `units: minutes`, `type: duration`, `configurable: true`, `gap: GAP-0042` (`docs/registry/variables.yaml:438-460`), note: "Fifteen minutes was tentative and is not a live value."

**Old wiki:** "Window is explicit UTC start/end (`window_start_utc`, `window_end_utc`) — the directive carries the window, **not a minutes-offset**" (`contracts/ct-bms-04-news-block-directive.md:28-29`); no minutes value appears anywhere in that corpus.

**Old spine / DEC-LOG:** "Blocking rules (impact tiers, pre/post window widths) are **DEC-linked registry variables**" (`ARCHITECTURE-SPINE.md:204`) — i.e. the widths are node-side parameters that *produce* the bounds. Operator's own recalled wording, 2026-08-10, verbal and unratified: "halts all trading for **~5–15 min** around news; **buffer-before = buffer-after**; re-opens after the buffer; some sessions are unaffected by a given news time" (`DECISIONS-LOG.md:36`).

**Oldest layer:** the only place minutes were ever written down — MEDIUM `T-5 → T+10`, HIGH `T-15 → T+20`, EXTREME `T-30 → T+60 then YELLOW` (`02-Components/09-kill-switch-authority.md:85-90`), plus a staggered 25%-per-2-minutes exit ladder T-13..T-5 (`:328-336`). All of it sits on machinery ruled dead (TIGHTEN, DEC-0019; region shift, DEC-0021) and none of it was ever carried forward.

Precedence result: the *contract* carries instants (three layers agree); the *widths* are node policy and stay unratified.

### (2) Bucketing — **both**

QMF: the window is two instants, full stop. Node: the width policy that computes them, plus the "buffer-before = buffer-after" symmetry if the operator wants it.

### (3) Recommended ruling

The control-window record carries `window_start` and `window_end` as instants and nothing else about duration. Width parameters live node-side as declared configuration with **no default** (the spine's do-not-default standing, AD-27/AD-28) — their existence is mandatory, their value is not QMF's. `news_blackout_before` / `news_blackout_after` stay null until the operator gives a number backed by something.

Alternatives weighed. *(a) Store the offsets in the record and compute bounds at read time* — rejected: it makes a window's meaning depend on a policy version rather than on the record, which breaks replay (the same record would block differently under a later policy). *(b) Ratify the operator's recalled 5–15 minutes now* — rejected: AD-13 and FM-6 forbid it, and the recalled figure is a range, not a value.

### (4) What would change it

Nothing structural. A ratified width changes only the node's parameter, never the contract.

---

## NEWS-4 — Severity, and what happens when the calendar is uncertain

### (1) Evidence

**Current:** GAP-0042 names "severities" as unresolved; nothing else exists.

**Old wiki:** the only severity notion is the word "high-impact", plus the conservative rule — "if high-impact coverage is unknown after fallback, blocking is **conservative and visible**"; "Forex Factory primary and verified impact-carrying fallbacks" (`ct-bms-04:38`). No tier ladder with thresholds. Calendar refresh is "a daily pre-trading-day ritual, journaled".

**Old spine:** "Calendar impact enum is **high/med/low** (Forex Factory)" (`ARCHITECTURE-SPINE.md:376`), fallback chain FMP → Trading Economics → FXStreet behind one normalized import, every import journaled, failed refresh degrades visibly with notification.

**GitBook:** news is a **binary block**, not tiered; the only tiering nearby is `CT-NOTIFY-01`'s operator-alert tiers P1..P4, which are unrelated (`contracts/ct-notify-01:17`). KSA `trigger_class` includes `scheduled_news` but the trigger→level matrix is GAP-0015, open.

**Oldest layer:** the full four-tier ladder (LOW/MEDIUM/HIGH/EXTREME) with per-tier KSA levels and windows — the only complete severity design that ever existed, and it is welded to the dead TIGHTEN level and the dead region-shift rotation.

Precedence result: keep the **provider's own impact label as recorded evidence**; do not re-grade it inside QMF; the tier→behavior map is node policy and currently has exactly one ratified rule — block conservatively when coverage is unknown.

### (2) Bucketing — **both**

QMF: the provider's impact label rides the control-window record as a recorded provider-native field, verbatim, never normalized into a QMX severity scale (AD-19 "foreign … is evidence"; AD-21 idempotent intake keyed on `(source, source-native id, revision)`). Node: which impact classes produce a window, and how wide.

### (3) Recommended ruling

V1 blocks on **high-impact only**, with one buffer width used before and after, and **blocks conservatively whenever coverage is unknown or the refresh failed** (the one rule three layers already agree on). Provider impact labels are stored as given; QMX mints no severity scale of its own in V1.

Alternatives weighed. *(a) Revive the four-tier ladder* — rejected: it is inseparable from TIGHTEN (dead, DEC-0019) and from a staggered soft-exit ladder that is a position-closing behavior nobody has ruled (see NEWS-5). *(b) Block on all impact classes* — rejected: it converts a forex scalper's day into mostly-blocked with no evidence that low-impact events move spreads enough to matter — but this is exactly the operator's call, not mine, hence the question. *(c) Let QMX re-grade impact from measured post-event volatility* — noted and deferred: it is a legitimate later idea, it needs measured evidence that does not exist, and it would be a new governed producer, not a news rule.

### (4) What would change it

Measured spread/volatility evidence around medium-impact releases would justify a second class. A provider change (the source chain is data-sitting territory under AD-21, and the legal archiving posture there is still an open operator item) changes the label vocabulary but not this ruling, because the label is stored verbatim.

---

## NEWS-5 — Open positions when a window opens (five-hats T-6)

### (1) Evidence

**Current:** unresolved and explicitly named: GAP-0042 lists "open-position behavior"; `GAP(GAP-0046): Define deterministic same-tick priority` (`docs/components/qmf-risk.md:85`); AD-27 hands the question here — "Flatten is `close_position`/`close_all` executed mechanically; **the adapter never initiates it; authority assignment (VPS-death included) belongs to the risk/node sittings**" (spine:276).

**Old wiki:** "News block blocks **new entries** for affected pairs live+paper"; "**Behavior of ALREADY-OPEN positions under a news block is NOT specified**" — folded into PE-7, the open position-fate blocker (`components/kill-switch-authority.md:38`, `scn-0003-news-block.md:36-37`, `knowledge/gap-report.md:42`). The 2026-07-28 interim is stricter still: "**No position flatten or carry behavior is implemented anywhere in V1 until PE-7 is ruled**" (`topics/position-safety-and-sltp-authority.md:75-81`).

**GitBook:** SCN-0003 tests refusal of *new candidate entries* only; nothing addresses open positions.

**Oldest layer:** the only design that ever existed — staggered 25% exits every two minutes from T-13 to T-5, target 0% exposure at T-5, weight ×0.1 until T+15 (`09-kill-switch-authority.md:328-336`). Dead machinery, but it is the operator's original intent and worth naming when he rules.

Precedence result: genuinely unruled at every layer above the oldest. This is a decision, not an inheritance.

### (2) Bucketing — **re-buckets to node**

The behavior is node runtime. What QMF still carries: **a rank slot**. Five-hats T-6 is right that this must not become a separate code path — if a window can close positions, "news force-flat" is a rung in the same-tick priority order alongside KSA effects, hold-time force-flat, broker-resident stops, and ordinary amendments, and it is ranked in the same contract that ranks them. QMF also carries the typed close command already ratified: `close_position`/`close_all` with a required typed scope `account | account-binding | instrument-within-binding` (AD-27, spine:271) — a pair-scoped news flatten is exactly `instrument-within-binding`, and CT-18 must declare that scope natively supported or the flatten refuses rather than being emulated at a wider scope.

### (3) Recommended ruling

**V1: a news window stops new entries and does nothing to open positions.** The bot's own exit organs and its protective stop remain the only thing acting on an open position during a window. If the operator later wants a pre-news flatten, it enters as a ranked rung — never a bypass — and it must declare `instrument-within-binding` scope.

Why I lean this way. Three reasons, in order of weight. First, a news flatten is a *market order into the thinnest liquidity of the hour* — the staggered ladder in the oldest design exists precisely because the author knew a single flatten at T-5 pays a spread that the block was supposed to avoid, and reviving the ladder means reviving a graduated-exit organ nobody has designed. Second, it collides with the one thing this sitting has been told to fix: flatten authority is UNASSIGNED, and assigning it to an automated calendar entry is the largest possible first grant. Third, PE-7's interim ruling — no flatten or carry behavior anywhere until ruled — is the most recent position on record and points the same way.

Alternatives weighed. *(a) Flatten all affected positions before the window* — the operator's original intent, and defensible for a scalper whose positions are minutes old; it needs the priority rank and a scope declaration first, which is why it is offered as the alternative in the question rather than dismissed. *(b) Tighten stops instead of closing* — rejected: stop-amendment authority is itself unresolved (DEC-0067, GAP-0040), so this ruling would silently decide exit ownership as a side effect. *(c) Freeze exits during the window* — rejected outright: it removes protection exactly when protection is needed.

### (4) What would change it

Measured evidence that positions held through high-impact releases lose more than a flatten's slippage costs would flip it. So would the operator simply preferring flat-before-news, which is a legitimate preference and not something evidence has to earn.

---

## NEWS-6 — Which revision a decision evaluates, and late revisions (five-hats T-5)

### (1) Evidence

**Current:** AD-21 requires the news-calendar recorder to keep "provider-native identity and revisions"; AD-19 makes `(event-time, known-at, source, revision)` mandatory on every external fact and rules that "corrections are appended, never overwrite"; AD-21's intake is "idempotent … keyed on (source, source-native id, revision) — **a provider revision is a new artifact, never an AD-10 collision**" (spine:191). AD-25 binds a consumer to "the revision known at observed-at" (spine:244). AD-8: "Causality is compared on instants only" and causality tests "refuse at equal instants rather than tie-break" (spine:94, :97).

**Old wiki:** the only override-shaped rule in any corpus — "Session scoping **may widen a block but may not narrow it**. Sessions remain informational, not authority" (`ct-bms-04:37`).

**GitBook / oldest:** silent on revisions entirely.

Precedence result: the framework half is already ratified; only the risk-side behavior of a mid-window revision is open.

### (2) Bucketing — **both**

QMF: the revision-bearing record and the knowable-at discipline (already ratified). Node: what a late revision does to a live window.

### (3) Recommended ruling

Three lines, all forward-only:

- A decision evaluates the **revision knowable at decision time**. A replay of that decision resolves the same revision, so blackout behavior is reproducible.
- A revision arriving mid-window may **widen** — pull the start earlier for instants not yet passed, push the end later — and may **never narrow, cancel, or retro-invalidate** a window that has already had effect. This is the ratified widen-never-narrow rule applied to time instead of sessions.
- A revision revealing that a window *should* have opened earlier opens it **now**, forward only. Decisions already taken under the older revision **stand**, and are tagged with the revision they ran under (NEWS-8) so the analyst can see the discrepancy rather than reading it as decay.

Alternatives weighed. *(a) Retro-open and flatten what was opened in the missed period* — rejected: it is a retroactive automated close driven by a third party's data correction, which is the worst possible first use of flatten authority. *(b) Refuse the whole window on a conflicting revision* — rejected: it fails open on a safety control. *(c) Re-evaluate all decisions under the newest revision* — rejected: it violates AD-8 causality and makes replay non-deterministic.

### (4) What would change it

If the provider's revision stream turns out to move event *times* routinely rather than rarely, the node may want a "revision churn" data-quality alarm; that is a threshold, not a change to these three lines.

---

## NEWS-7 — Overrides

### (1) Evidence

**Current:** GAP-0042 names "overrides" as unresolved. Nothing in the current corpus grants a human news override. The one ratified human power in the neighbourhood is the A1 gate — "Automated KSA transitions escalate only; **de-escalation requires A1 human authority**" — and news is not KSA.

**Old wiki:** "**No human override path defined** (system is unattended; L3)"; sessions may widen never narrow (`ct-bms-04:37`, `invariants.md:21`).

**GitBook:** "Overrides: not found anywhere."

**Oldest layer:** the only override that ever existed was for region rotation — "default auto-rotate, log, no prompt; operator can override" (`09-kill-switch-authority.md:378-425`) — and region shift is dead (DEC-0021).

Precedence result: no override has ever existed for a news window at any layer. Silence here is consistent silence, not a gap.

### (2) Bucketing — **re-buckets to node** (QMF carries nothing extra)

### (3) Recommended ruling

No discretionary narrowing, skipping, or "trade through it" switch in V1. A window may be widened (by session scoping, by a revision) and never shortened. The operator's power over news is upstream — which impact classes block, how wide the buffer is — exercised as configuration between sessions, not as a live button.

Alternatives weighed. *(a) A live per-window skip* — rejected: the system is unattended by design (L3), and a skip button that is only reachable when the operator happens to be watching produces behavior that cannot be replayed or explained. *(b) A standing per-instrument exemption list* — genuinely reasonable and worth having if the operator wants it (e.g. an instrument he judges unaffected by a given currency's releases), but it should be a *declared, dated, fingerprinted exemption record* consumed by the compile step, not a live override — i.e. the same shape as NEWS-2's currency-exposure record. If the operator says yes to an exemption capability, it lands there.

### (4) What would change it

An operator preference. This is his discretion to keep or give away, and the recommendation is only that giving it away is safer for a system that runs while he sleeps.

---

## NEWS-8 — Suppressed actions and evidence tagging (five-hats A-7, X-6)

### (1) Evidence

**Current:** AD-21 ratifies seven journal event types — "decision, order, fill, risk transition, promotion, **data quality**, **control action**" (spine:191) — and AD-28 already journals "adapter-initiated state changes (suspend-new, drain, session restart, throttle engaged, reconnect) … as `control action`" (spine:291). AD-12 keeps paper/demo at `world = live` "so paper/demo runs … stay comparable to live for alpha-decay sensing" (spine:136). Five-hats A-7: suppressed actions are "the highest-value analytic dataset in the system"; X-6: evidence produced under an active control comes "from a population the live Book was forbidden to trade — same world, same label shape, non-comparable content."

**Old wiki / GitBook:** every refusal already signs the veto ledger and emits CT-BMS-05, and refusals carry a door and a reason (`ct-book-01:36`, `ct-bms-05:36`) — the culture exists; the typed *suppression* record does not.

### (2) Bucketing — **both**

QMF: a **suppression** shape on the journal — suppressing authority, reason class (news window / SQS / kill switch / breaker / budget), the controlling window or reading's fingerprint, and the would-have-been action — carried as a `control action` subtype under AD-21's already-ratified event set, so no new event type is minted. Plus: any evidence record produced while a control was active carries the controlling record's fingerprint as an identity-bearing input. Node: emitting them.

### (3) Recommended ruling

Type it. Every refusal caused by a news window (or an SQS block, or a kill-switch effect) writes a suppression record naming the authority, the reason class, the controlling fingerprint, and what would have happened. Any evidence produced under an active control is tagged with that control's fingerprint.

Why: without it, every gate the system fires looks like alpha decay to the analyst, and the operator's decay signal is contaminated by his own protection. It is nearly free — the journal, the event type, and the fingerprints all already exist.

Alternatives weighed. *(a) Leave it as generic refusal log text* — rejected: log text is not journal evidence under AD-14 ("Logs are not journals"), and it cannot be queried into a cohort. *(b) Mint a new journal event type* — rejected: `control action` already covers it and AD-21's seven types are addable-never-redefined; a subtype is cheaper and keeps the catalog stable.

### (4) What would change it

Nothing I can see. This is the delegation-safest item in the cluster.

---

## NEWS-9 — The dead zone (~45-min session handover)

### (1) Evidence

**Current, operator, 2026-08-20:** "Dead zone: **~45-minute relax around session handover** (analysis-before-execution; from the first QMX version, operator-solved ~Dec 2025). Operator clarification 2026-08-20: the dead zone **pauses TRADING ONLY — data streaming continues** throughout; it is **NOT kill-switch logic**. Related note: real session activity starts later than nominal opens … session-open cross-referencing is a node-era refinement. **Risk-sitting policy.**" (`tracker/trading-node-notes.md:18`). Also on record: "Operator wants possibly all sessions traded; sessions resolved by **calendar rules + tz database**, never device/broker location" (`:20`).

**Old wiki / GitBook / recovery:** **not found anywhere.** The only "45" in those corpora is `order_latency_max_ms = 45` (unrelated). Worse for revival: "session windows as trading authority" is an explicitly **dead decision** (DEC-0025) — "the clock alone does not authorize trades … session context may only inform them if ratified" (`components/book-template.md:63`).

**Oldest layer:** an analogue exists but does not match — "OVERNIGHT | 19:00–20:00 | Dead zone — **no new positions advised**" (`02-Components/01-risk-and-sizing/05-session-architecture.md:32`), a **1-hour** window, not 45 minutes, and advisory rather than blocking. Adjacent: a 25-minute `SESSION_WARMUP` gate on the London/NY overlap with rejection code `SESSION_WARMUP` (`05-session-architecture.md:245-279`).

Precedence result: the dead zone exists **only** as a current operator statement. There is no prior art to inherit, and the nearest prior art (session-as-authority) is dead. The ~45 minutes stays an unratified number.

### (2) Bucketing — **both**

QMF: the same control-window record as NEWS-1, produced from a market-hours calendar (AD-8's calendar is the session-schedule authority, and a civil-time bucket key derived from an instant + zone + tzdata is explicitly "a legitimate computed value", spine:103) — so the dead zone is a *calendar-derived window*, not a hardcoded clock rule, which is exactly what the operator's "calendar rules + tz database, never device/broker location" demands. Node: the pause behavior, the width, and whether it applies per session pair or globally.

### (3) Recommended ruling

Express the dead zone as a control window from the same contract as news, produced by a market-hours calendar, with data ingestion explicitly unaffected (the record blocks *actions*, never *observation* — worth stating in the contract because the operator raised it unprompted). The ~45 minutes and the exact handover anchors stay unratified. It is not kill-switch logic and must not be routed through the protection funnel.

The open question is what "relax" means. The operator's word is *relax*, not *block*. A hard "no new entries" is the reading consistent with "pauses trading only", but a softer reading (reduced size, or entries allowed only on the session already open) is available and materially different — hence the question.

Alternatives weighed. *(a) Make it a distinct mechanism* — rejected: two window mechanisms means two priority stories, two evidence shapes, and two places to get the tz handling wrong. *(b) Route it through the kill switch as a scheduled level* — rejected explicitly by the operator's own 2026-08-20 clarification. *(c) Revive session-warmup as its own gate* — noted: the oldest layer's 25-minute overlap warm-up is the same idea under a different name, and if the operator wants both a handover pause and a post-open warm-up, both are windows from one contract.

### (4) What would change it

If "relax" means size reduction rather than a pause, the record needs an effect class beyond block/allow, and the node needs a sizing hook — which drags in the dead multiplier-stack territory (DEC-0018) and would need care.

---

## NEWS-10 — Does a news window stop paper too? (a conflict the sweep introduces)

### (1) Evidence

**Corpus, unanimous across three layers.** GitBook constitution L9: "News-affected currency pairs are blocked for **all books in live and paper mode**. DEC-0010." CT-KSA-01 rule: "News-affected currency pairs block live and paper." CT-BMS-04 rule: "Directive applies to live and paper books." SCN-0003, with the reason stated: "Both entries are refused … **no paper data is collected under a known invalid news window**. DEC-0010"; the fixture asserts "live and paper produce the same refusal class for the same affected pair and window." Old wiki and old spine restate it identically (`ct-bms-04:36`; PRD FR-20; `epics.md:1453-1465`).

**Five-hats, contradicting it.** T-6: "the operator's ruling so far covers only halting new entries **while letting bots continue in paper mode so decay data keeps flowing**"; X-6 builds a whole conflict on that premise.

**Current corpus:** carries neither side — paper-mode scope is itself an open contradiction on record (`tracker/trading-node-notes.md:25`: "fail-mechanism-only vs standing-state feeding alpha-decay").

Precedence result: three layers say block paper; the sweep's premise has no citation behind it and reads like a restatement of the *kill-line stand-down* (book flips to PAPER and keeps running) rather than a news ruling. But it names a real want — decay data through blackouts — and that want deserves an answer, not a correction.

### (2) Bucketing — **re-buckets to node** (QMF carries the tagging from NEWS-8)

### (3) Recommended ruling

**Block paper too**, per the unanimous corpus and its stated reason: data collected in a known-invalid window is poisoned evidence, and evidence collected under an active control is exactly the non-comparable population X-6 warns about. If the operator wants decay data to keep flowing through blackouts, the correct instrument is the **tag** (NEWS-8), not the trade: let the analyst include or exclude blackout-period evidence deliberately. Trading paper through a window to preserve comparability with a live Book that was forbidden to trade produces the opposite of comparability.

Alternatives weighed. *(a) Paper keeps trading, tagged* — the five-hats reading; it gives a richer dataset at the cost of a population the live book can never match, and it silently answers "is paper a standing state or a fail mechanism" in favour of standing state, which is a separate open question (`tracker/trading-node-notes.md:25`) that should not be decided as a side effect of a news ruling. *(b) Paper keeps trading, untagged* — rejected outright.

### (4) What would change it

The paper-mode scope ruling elsewhere in this sitting. If paper is ratified as a standing evidence-gathering state rather than a fail mechanism, this should be revisited **in that pass**, not here.

---

# Part B — GAP-0043, SQS

`GAP(GAP-0043): Define SQS inputs, units, formula, thresholds, cadence, hysteresis, and stale-data behavior.` (`docs/components/qmf-risk.md:79`).

**Standing instruction honoured below: no formula is proposed.** Part B assembles the complete old candidate for the operator's re-understanding pass, proposes only the contract *shape*, and lists what stays open.

---

## SQS-1 — What SQS means (settled, recorded for the pack)

**Current, ratified:** "SQS means **Spread Quality Sensor**" (`docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:31`, DEC-0074). The glossary retires the rival reading explicitly: "**Snapshot Quality Sensor: Incorrect expansion of SQS. Use SQS.**" (`docs/glossary.md:550-552`). "SQS is distinct from news control" (`:408-410`).

**Operator ruling 2026-08-17** agrees and adds the mechanism sketch: "SQS means **Spread Quality Sensor**. The legacy mechanism compares instrument-aware historical spread with current live spread, emits score/hard-block evidence, and grants MIS no trade authority" (recovery addendum:64; `trading-node-delta.md:96` K-38).

**Old wiki said the opposite:** "SQS means **snapshot quality score**" (`components/market-intelligence-service.md:46`, `ct-mis-01:38`, `glossary/index.md:79`), and the old node build ratified a matching six-component aggregate as Story 3.1. The 2026-08-17 ruling kills that reading for this name: reject "snapshot quality score" as the meaning of SQS; "Reopen separately under a different name if wanted" (`trading-node-delta.md:190` D-09; addendum:95-104).

**Precedence result: Spread Quality Sensor.** No operator question needed — two independent current-layer sources agree, and the losing reading is explicitly retired by name.

One caveat worth carrying: the six-component aggregate is not *wrong*, it is *a different sensor*. Its component set (spread, gap, liquidity, feed, sensor-freshness, regime quality) overlaps what MIS already publishes as separate CT-MIS-01 fields. If the operator ever wants an overall "is this snapshot trustworthy" number, it comes back under its own name and its own gap — never as SQS.

---

## SQS-2 — RE-UNDERSTANDING PACK: the complete old candidate

Everything below is **recorded evidence for the operator to read, not a proposal.** It is assembled from the oldest layer (where the full design lives), the two intermediate layers (where only the interface survives), and the operator's own 2026-08-17 recall. Nothing here is ratified; several parts are on dead lists, flagged inline.

### 2a. What it measured — the formula, verbatim from the oldest layer

`02-Components/05-spread-quality-service.md:42-43`:

```
sqs_score = historical_avg_spread(symbol, session_window) / current_live_spread(symbol)
```

> "A score of **1.0** means the current spread exactly matches the historical average. A score **above 1.0** means … tighter than average … A score **below 1.0** means … wider than average."

The operator's 2026-08-17 recall matches it exactly, in the same direction: `sqs_score = historical_average_spread / current_live_spread`; "`1.0` means baseline spread, above `1.0` means tighter, and below `1.0` means wider" (recovery addendum:88-92).

**Read the shape before the number:** it is a *ratio against that instrument's own normal*, not an absolute spread threshold. A 2.0-pip spread is fine on one instrument and an alarm on another; the ratio is what makes one sensor work across a book of instruments.

### 2b. The denominator's conditioning

`05-...:48-52`: the historical average is **per canonical session window**, not a flat 24-hour average. (i.e. "normal for EURUSD at the Tokyo/London handover" ≠ "normal for EURUSD".)

### 2c. Hard-block thresholds, per instrument category

`05-...:77-83`: Major FX **0.60** · Minor FX **0.55** · FX exotic **0.45** · Index CFDs **0.65** · Commodity CFDs **0.50**. Per-symbol and per-session overridable via config (`:85`).

### 2d. Hysteresis

`05-...:88-89`: "once `hard_block=True` is set, the score must exceed `hard_block_threshold + hysteresis_band` (**default 0.05**) before `hard_block` reverts to `False`." — i.e. a deliberate anti-flicker band so the gate does not chatter on and off around the line.

### 2e. Outlier guard

`05-...:133-137`: if `current_live_spread > historical_avg_spread + 4 × historical_std_spread` → `hard_block=True`, `sqs_score` clamped to `0.0`, `quality_tag=DEGRADED`.

### 2f. Cadence and recompute schedule

`05-...:122-129`, `:222-224`: computed **per quote update during an active session**, ≤3 ms per quote; the baseline recomputes **daily, 30 minutes before the Tokyo open**; a **full re-fit weekly, Sunday 22:00 UTC**.

### 2g. Undefined / weekend behavior

`05-...:54-56`: when the score is undefined (weekend, illiquid), a sentinel `-1.0` is published and treated as an implicit halt on entries. Conservative-by-default throughout: "every ambiguous/failed state → `hard_block=True`" (`:216`).

### 2h. Soft sizing ladder — ON THE DEAD-ADJACENT LIST, recorded for completeness

`05-...:99-105`: score ≥0.90 → ×1.00; 0.75–0.90 → ×0.85; 0.65–0.75 → ×0.70; threshold–0.65 → ×0.50; below threshold → hard block. This is a declared-weight sizing multiplier, the family ruled dead by DEC-0018 and re-killed in the current corpus's never-list. See SQS-5 — it is the one live question the ladder raises.

### 2i. Authority boundary — consistent across every single layer

- Oldest: "SQS computes; MIS transports `sqs_hard_block`; **the Risk Authority decides the block**" (`05-...:17`, `:73`).
- GitBook: "Snapshot is information-only"; "**SQS unreachable creates a hard door block**. DEC-0042"; MIS "never sizes/blocks/trades" (`contracts/ct-mis-01:20-21,28`; `components/market-intelligence-service.md:26`).
- Old node build: "SQS is deterministic evidence only; **it does not authorize or execute a trade**" (`standards/labeler-catalog-ratification.json:232`).
- Operator 2026-08-17: "let MIS carry that evidence **without acquiring trade authority**; let the Book's relevant door decide the refusal; **fail closed** when spread quality cannot be established" (addendum:78-84).

**Four layers, one boundary.** This is the most consistent fact in the entire risk corpus and it is the spine of the shape proposal in SQS-3.

### 2j. Why it existed

`05-...:15`: "it carries symbol-aware baseline data … its hard-block signal is **one of the few inputs capable of informing an unconditional no-entry decision** regardless of regime state or position-sizing output." In the GitBook layer it becomes a door input feeding the footprint/viability veto. In plain words: *a scalper's edge is measured in a handful of pips, so an abnormally wide spread does not shrink the edge, it deletes it — and no amount of good signal can pay for it.*

### 2k. What the intermediate layers kept (interface only, no math)

CT-MIS-01 fields, identical in wiki and GitBook: `spread_state ∈ [normal, elevated, extreme]`, `sqs_score` (number), `sqs_hard_block` (boolean), alongside `gap_event`, `liquidity_stress`, `feed_state ∈ [fresh, stale, dead]`, `degraded_sensors[]`. No formula, no threshold, no cadence, no hysteresis anywhere in either corpus (whole-corpus grep for "hysteresis" in the GitBook capture: zero hits).

### 2l. The rejected aggregate (recorded so nobody re-imports it as SQS)

Old node build, `standards/labeler-catalog-ratification.json:294-363`: `sqs_weighted_component_floor_v1`, scale 10000 bp, six inputs each 0..10000 bp — feed 2500, spread 2000, gap 1500, liquidity 1500, sensor freshness 1500, regime 1000 (sum 10000); `score_bp = floor(Σ(quality_bp × weight_bp) / 10000)`; a minimum reachable floor below which the score refuses; unreachable → `sqs_hard_block: true`; typed refusals `SQS_INPUT_REFUSED`, `SQS_UNKNOWN_COMPONENT`, `SQS_FORMULA_DRIFT`. Its component thresholds are also on record (`:99-205`): spread_state normal ≤12 points, elevated ≤25, extreme >25; feed fresh ≤1000 ms, stale ≤5000 ms, dead >5000 ms; tick-gap 1500 ms.

**Ruled not-SQS** by the operator on 2026-08-17. But one thing in it is worth keeping regardless of what formula lands: **integer basis-point arithmetic**. Under AD-10, "floats are refused in identity content"; under AD-7, every non-integer parameter is an exact rational. A float ratio cannot be an identity field. Whatever SQS formula is ratified, its score, its thresholds, and its hysteresis band must be exact rationals (scaled integers or numerator/denominator) — the rejected aggregate got that discipline right even though it got the meaning wrong.

### 2m. Dead / do-not-revive, adjacent to SQS

- "Snapshot quality score" as the meaning of SQS (operator ruling 2026-08-17, D-09).
- Declared-weight sizing multiplier stacks (DEC-0018; current never-list, `docs/components/qmf-risk.md:23-24`).
- Session windows as trading *authority* (DEC-0025) — sessions may **inform** a computation, never authorize a trade. This matters here: conditioning the baseline on a session window is *informing*, and is fine; letting the session clock itself gate entries is dead.

---

## SQS-3 — Contract shape (the only thing proposed)

### (1) Evidence

The boundary is unanimous (2i). The spine supplies the rest: AD-22 makes a value-per-evaluation-instant producer a **CT-16 configured indicator** whose "**identity = the entire declared configuration**", including formula id, exact parameters, the ordered named input set, declared calendar requirements, warm-up, and output schema (spine:201); it permits typed configuration inputs including market-hours calendars and instrument-metadata snapshots (spine:202); every sample carries a **knowable-at instant** (spine:206); missing-vs-closed is explicit, with `absent_by_schedule` distinct from a gap and no silent filling (spine:207). AD-11 already ships `stale evidence` and `unavailable dependency` as categories. AD-24 requires anything on the live decision path to declare **light** and benchmark-prove it — and "until the live-path rung has a recorded baseline, every configuration is heavy by default and a light claim is refused at the gate" (spine:231). AD-25's routing test settles the placement: "a value per evaluation instant is CT-16" (spine:247).

### (2) Bucketing — **both**

**Stays QMF:**
- **The sensor as a governed producer** — a versioned pure function over bid/ask quote evidence plus session context, fingerprinted by its entire declared configuration, emitting an exact-rational score channel plus a typed availability marker, with a declared baseline input, declared warm-up, and a knowable-at on every sample. Its baseline (the "historical average spread for this instrument in this session window") is itself a **fingerprinted derived artifact** with its own refit cadence — not a config constant — so a refit mints a new artifact with a lineage edge (AD-5) rather than silently changing the sensor's meaning.
- **Typed outcomes:** unavailable, stale, and refused are AD-11 categories, not sentinel numbers. The oldest layer's `-1.0` sentinel is exactly the pattern AD-22 prohibits ("NaN and sentinel markers are prohibited", spine:199) — the same *behavior* survives as a typed marker.
- **A reading slot on the risk-evaluation contract** carrying the score, its knowable-at, and its availability state into whatever evaluates a trade intent.

**Re-buckets to node:** the threshold, the hysteresis band, the block decision, and the door that refuses. QMF senses and refuses to answer; the node decides.

### (3) Recommended ruling

Ratify the **shape** now — versioned pure function over bid-ask evidence + session context, exact-rational output, typed stale/unavailable outcomes, fingerprinted baseline as a declared input, no trade authority — and ratify **no formula, no threshold, no band, no cadence** until the operator's re-understanding pass.

Alternatives weighed. *(a) Ratify the old formula now* — refused by instruction and by judgment: the operator asked for a re-understanding pass first, and the old formula's denominator conditioning, baseline window, and per-category thresholds all need his eye. *(b) Make SQS a node-private computation* — rejected: it would be an ungoverned number gating live money, unfingerprinted and unreplayable, and it would put spread arithmetic outside AD-23's canonical-arithmetic discipline. *(c) Make it a structure family (CT-17)* — rejected by AD-25's routing test; it is a value per instant, not an object with a lifetime.

### (4) What would change it

If the operator rules that SQS also shrinks size (SQS-5 = yes), the score becomes **money-path tainted** under AD-7 — it would transitively contribute to an order quantity — which hardens the exact-rational requirement from good practice into law and pulls the sensor into the money-path audit surface. That is a real consequence and it is why SQS-5 is asked rather than assumed.

---

## SQS-4 — Unreachable or stale SQS

### (1) Evidence

Every layer says the same thing. GitBook: "**SQS unreachable creates a hard door block**. DEC-0042"; failure-mode table "SQS unreachable → Door performs hard block." Old wiki: identical. Old node build: unreachable → `sqs_hard_block: true`, `trade_authority: false`. Oldest layer: "every ambiguous/failed state → `hard_block=True`" and the weekend sentinel implies halt. Operator 2026-08-17: "**fail closed** when spread quality cannot be established." Current: stale-data behavior is listed as open under GAP-0043 — the only layer that does not state it, because it states nothing about SQS at all.

### (2) Bucketing — **both** (QMF returns the typed refusal; the node fails closed on it)

### (3) Recommended ruling

Fail closed. An unavailable, stale, or refused SQS reading blocks new entries; it never degrades silently and never passes a stale number through. QMF returns `stale evidence` / `unavailable dependency`; the node treats either as a block. The *staleness horizon* itself is a number and stays unratified — five-hats T-9 correctly assigns "how old is too old" to the data sitting as a declared freshness horizon on the evidence contract, per observation kind.

Alternatives weighed. *(a) Use last-known-good on a stale reading* — rejected: a stale spread reading during a liquidity event is precisely the case the sensor exists to catch. *(b) Treat unavailable as neutral* — rejected by five layers of agreement.

### (4) What would change it

Nothing. This is delegation-safe.

---

## SQS-5 — Does SQS ever shrink size, or only block?

### (1) Evidence

**Oldest layer:** yes — the soft multiplier ladder in 2h (`05-...:99-105`).
**Every later layer:** no such thing exists; SQS appears only as a score plus a hard-block boolean.
**Current:** declared-weight multiplier stacks are on the never-list (`docs/components/qmf-risk.md:23-24`, DEC-0077/0079/0093 territory; the parent family DEC-0018).
**Adjacent constitutional rule (GitBook L12, DEC-0013):** "Graduated policy shrinks before it blocks **unless the event class demands instant action**" — which argues *for* a graduated response in general, and is the strongest thing in the corpus on the pro-shrink side.

Precedence result: genuinely two-sided. The dead list kills *stacks of declared weights*; a single spread-driven size taper is not obviously the same object, and L12's graduated principle points the other way.

### (2) Bucketing — **node** (QMF carries the reading either way; only the money-path taint changes)

### (3) Recommended ruling

**Block-only in V1.** Reasons: it keeps the sensor off the money path (AD-7), which keeps the exactness burden and the audit surface smaller; a taper ladder is a set of invented numbers on top of a formula that is not yet ratified; and the pro-shrink argument (L12) is weakest exactly where spread is concerned — a wide spread does not shrink the edge proportionally, it consumes a fixed cost per round trip, so half size in a double spread is still a losing trade (FORM-0007's viability floor, `round_trip_cost_R / expected_edge_R <= v_cost`, is the same insight already expressed as a door).

Alternatives weighed. *(a) Restore the taper ladder* — coherent with L12 and with the operator's original design, and defensible if he wants degradation rather than a cliff; the cost is money-path taint plus five more unratified numbers. *(b) Two thresholds — a taper line and a block line* — the middle option, and the one to reach for if he dislikes the cliff but not enough to want a five-rung ladder.

### (4) What would change it

Measured evidence that entries taken at 0.7–0.9 spread quality are profitable-but-worse, rather than unprofitable, would justify the taper. That evidence does not exist and cannot exist until the sensor runs.

---

## What stays open after this sitting (GAP-0043 residue — must remain null)

Per FM-6 and AD-13, none of the following may be invented, and all should be recorded as still-null when the sitting writes its gaps:

1. The **formula** (the old ratio candidate is assembled in SQS-2; the operator rules after his re-understanding pass).
2. The **baseline definition** — window length, session conditioning, whether it is a mean or a quantile, and the refit cadence.
3. **Thresholds** — per instrument, per instrument class, or per session; the old per-category table (2c) is evidence, not a value.
4. The **hysteresis band** (old default 0.05 is evidence, not a value).
5. **Cadence** — per quote vs per bar vs per decision, and the AD-24 light-claim baseline that must be measured before SQS can sit on the live path at all.
6. The **outlier guard** (old: 4σ) and its interaction with the hysteresis band.
7. The **staleness horizon** for a spread reading — data sitting, per five-hats T-9.
8. Whether `spread_state`'s `normal/elevated/extreme` classification survives as a separate published field or is folded into the score.

---

# Operator questions

Recommendation first in every one. Each answerable yes/no or by a short choice.

### Q1 — How the system knows which instruments a news event touches

**Recommendation: never read it off the symbol name.** Keep a small declared table saying which currencies each of your instruments touches — filled in from what the broker tells us, correctable by you. If an instrument has no entry yet, treat it as affected and block it until you fill it in.

*Why this is a question:* the old design worked by reading "USD" out of the text "EURUSD". The new foundation forbids reading symbol text at all (it is what stops two brokers' records from silently mixing), so the mapping has to be declared instead of guessed.

**Is that the right trade — a small table you maintain, and block-if-unknown? (yes / no)**

### Q2 — Which news events block

**Recommendation: only high-impact events block, one buffer width used before the event and the same width after** (your own wording: buffer-before = buffer-after). And when the calendar refresh fails or coverage is uncertain, block anyway.

**Do medium-impact events block too? (no / yes / yes but with a shorter buffer)**

*(No minutes are proposed. The old "15 minutes" was withdrawn as tentative and stays withdrawn.)*

### Q3 — Positions you already have open when news hits

**Recommendation: leave them alone.** The window stops *new* trades; the position's own stop keeps protecting it. Closing into the thinnest liquidity of the hour usually costs more than it saves, and handing an automated calendar the power to close your positions is the biggest possible first use of a power that is currently unassigned.

**Leave open positions alone, or close them before high-impact news? (leave-alone / close-before)**

### Q4 — A manual "ignore this one" switch

**Recommendation: no.** A news window can be made *wider* but never shorter or skipped. Your control is upstream — which events block and how wide the buffer is — set between sessions, not clicked live. The system runs while you sleep, and a button only reachable when you are watching makes behavior you cannot reproduce or explain afterwards.

**Agree — no live skip button? (yes / no — and if no, would a standing per-instrument exemption list do instead?)**

### Q5 — Does news stop your paper bots too?

**Recommendation: yes, stop them too.** Every version of the documentation says so, with the reason written down: data collected during a known-invalid news window is poisoned — it tells you nothing about whether the strategy works. If what you want is performance data that keeps flowing through blackouts, the answer is to *label* the blocked periods so you can look at them deliberately, not to trade through them.

**Stop paper bots during a news window too? (yes / no)**

### Q6 — Your dead zone around session handover

**Recommendation: treat it as a hard "no new trades" window**, built from the same machinery as news, positions already open untouched, and data streaming continuing throughout (as you specified). The ~45 minutes stays unwritten until you give a number you trust.

*Why this is a question:* your word was "relax", which could mean a full pause or something softer.

**Is "no new trades" what you meant, or something softer like smaller size? (no-new-trades / smaller-size)**

### Q7 — The spread sensor: is this the thing you remember?

I have assembled the whole original sensor on one page — what it measured, its cut-off lines, its anti-flicker buffer, when it recalculated its baseline (see §SQS-2 of this brief). **No formula is being proposed and none should be ratified today.**

**Recommendation: confirm it matches your memory before anyone designs against it.** In plain words, the original was: *one number comparing today's spread on an instrument to what is normal for that instrument at that time of day, with a hard "do not trade" line below which entries are refused, and a small buffer so the gate does not flicker on and off around that line.*

**Is that the sensor you remember? (yes / no — and if no, what is missing?)**

### Q8 — Should the spread sensor ever shrink your size, or only block?

**Recommendation: block only, for now.** The old design had a size ladder (0.85 × … 0.70 × … 0.50 ×) below the block line. Half size in a doubled spread is still a losing trade — the spread is a fixed toll per round trip, so it does not get cheaper when you trade smaller. Block-only also keeps the sensor off the money path, which keeps the arithmetic rules simpler and the audit smaller.

**Block only, or also shrink size in the middle band? (block-only / also-shrink)**

---

## Handoff notes for the sitting

- **Sequencing:** Q3's answer feeds the same-tick priority ruling (GAP-0046). If "close-before" wins, news force-flat becomes a **ranked rung**, not a separate path (five-hats T-6), and it must declare the `instrument-within-binding` close scope that AD-27 requires — which the venue sitting's CT-18 must have declared as natively supported, or the flatten refuses rather than being emulated at a wider scope (T-4's dependency, in this cluster's concrete form).
- **Cross-cluster:** NEWS-8's suppression record is the same object five-hats A-7 asks for and the same tag X-6 needs; whoever writes the journal event catalog for this sitting should write it once for news, SQS, kill switch, breaker, and budget together.
- **To the data sitting:** the news-calendar recorder (AD-21) must preserve provider-native identity **and revisions**, or NEWS-6 is unenforceable; the staleness horizon for a spread reading (T-9) belongs there too.
- **Numbers that must remain null when this sitting writes its gaps:** `news_blackout_before`, `news_blackout_after`, `spread_quality_sensor_formula`, every SQS threshold and band, the dead-zone width. Fifteen minutes, 0.60, 0.05, 45 minutes, and 4σ appear in this brief as **evidence of what once existed** and nowhere as proposals.
