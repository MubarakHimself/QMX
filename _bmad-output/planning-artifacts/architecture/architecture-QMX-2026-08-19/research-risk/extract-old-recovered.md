# Risk-Sitting Evidence Dossier — Old Recovered Design Artifacts

**Extractor corpus:** `C:/Users/Mubarak/Documents/QMX/raw/local-cleaned/`
**Primary body:** `.../2026-07-20-recovered-design-artifacts/` (15 markdown files + `manifest.sha256`)
**Citation shorthand:** unless a full path is given, every `filename.md:NN` below resolves under
`C:/Users/Mubarak/Documents/QMX/raw/local-cleaned/2026-07-20-recovered-design-artifacts/`.

## Corpus provenance & layer labelling (READ FIRST — I record precedence, I do not decide it)

This corpus is **two evidentiary strata bundled together**, both captured/cleaned 2026-07-20
(`capture-metadata.md:1-10`); user explicitly approved for documentation ingest 2026-07-20
(`capture-metadata.md:6`); the thirteen captured markdown files are declared **immutable evidence,
interpretable only through authored `wiki/` pages** (`capture-metadata.md:8`).

1. **OLD-VAULT BASELINE (oldest layer = QMX-discussion / old-wiki era).** The `*-spec.md`
   extractions (`sltp-authority-spec.md`, `dpr-prs-spec.md`, `alpha-decay-spec.md`,
   `bot-registry-lineage-spec.md`, `backtest-engine-spec.md`, `qml-spec.md` Part B).
   Each self-labels its source "Canonical v1.0" and each extraction **explicitly voids that
   label**: "that label carries no authority now" / **"UNRATIFIED baseline"**
   (`sltp-authority-spec.md:6`, `dpr-prs-spec.md:5-7`, `bot-registry-lineage-spec.md:7`,
   `backtest-engine-spec.md:4`, `alpha-decay-spec.md:4`). Export dates 2026-07-17 / 2026-07-18.
   Substance predates the GitBook core.
2. **CLASH REPORTS & COMMENTARY (Claude personal analysis, 2026-07-18), reading the old vault
   AGAINST the GitBook new core.** These cite GitBook-layer rulings (DEC-####, GAP-####,
   L-invariants, CT-*, FORM-####, ADR-####). They are interpretation, not ratification; their
   own recommendations are marked "recommend" / "proposal, not translation"
   (`clash-report-sltp-vs-book.md:66`, `microservices-proposal.md:3`).

**Net:** raw mechanics below are **UNRATIFIED old-vault (oldest)**; every "what survives / what
dies / DEC-#### says" judgement is **GitBook-layer reasoning dated 2026-07-18**. This corpus does
**NOT** contain the verbatim new-core CT-BOOK / CT-BMS schemas, treasury pages, or venue-binding
pages — it only *references* them; those live in the GitBook/wiki corpora other extractors hold.

---

## Topic 1 — Book schema (CT-BOOK-01/02/03, versioned book-type schema, seven doors)

**Seven doors — FOUND, VERBATIM, in ratified order (twice, consistent):**

> "seven doors in ratified order (footprint → viability veto → R_max → daily budget → breaker →
> exposure ledger → KSA → adapter, DEC-0035)" — `clash-report-sltp-vs-book.md:15-17`

> "Seven doors (footprint, viability veto, R_max, daily budget, breaker, exposure ledger, kill
> switch); every refusal signs the veto ledger (L11)" — `qml-spec.md:159`

Note the two listings differ in tail rendering: the first appends "→ KSA → adapter" (8 arrows,
adapter as terminal enforcement), the second names the 7th door "kill switch" and stops. Both
GitBook-layer (2026-07-18). Door #1 = **footprint**, #3 = **R_max**, #4 = **daily budget**,
#5 = **breaker**, #6 = **exposure ledger**, #7 = **KSA / kill switch**.

**Charter grammar / money shape — FOUND (referenced, not schema-quoted):**

> "charter grammar including **money shape** (charter slot #2, DEC-0027); money-rule grammar is
> template-owned, values instance-owned (DEC-0026). Nothing post-entry." — `clash-report-sltp-vs-book.md:17-18`

Book **template governs the ENTRY side only** (`clash-report-sltp-vs-book.md:14`). Template/instance
split is ADR-0002 (`clash-report-sltp-vs-book.md:81`, `clash-report-backtest-replay.md:50`).

**CT-BOOK-01/02/03 field schemas: NOT FOUND** in this corpus (this corpus references the book
template/charter but never quotes CT-BOOK field lists). "Book §6 workspace" is an open new-core gap
FM-4 / DEC-0039 (`gaps-commentary.md:11`).

---

## Topic 2 — BMS schema (CT-BMS-*, BMS owns vs Book owns)

**FOUND (boundary rulings, not field schema):**

> "**BMS**: never trades, sizes, or reaches inside a book (DEC-0045)." — `clash-report-sltp-vs-book.md:23`

> "BMS Records owns the ONLY journal write path (DEC-0046 — this service only reads)" —
> `clash-report-bot-rating.md:79`; restated `microservices-proposal.md:40-41`, `qml-spec.md:155`.

BMS has **four desks** (`qml-spec.md:160`: "Four BMS desks + 17 CT-* contracts"); a Reporting desk
with **"zero authority"** (`clash-report-bot-rating.md:103-104`). BMS Records is the journal
authority; a Position-Safety service "journals via BMS Records; every amendment appended —
veto-ledger culture, L11" (`clash-report-sltp-vs-book.md:82-83`). "BMS §1–2 desk assignments" is an
open new-core gap, BMS FM-2 fences it ("no silent authority") (`gaps-commentary.md:20`).

**CT-BMS-* field schemas: NOT FOUND.** What a BMS *owns vs the Book*: BMS = journals/records/
reporting (zero trade/size/reach authority, DEC-0045/0046); Book = entry doors + money shape +
charter. No finer split in this corpus.

---

## Topic 3 — Cardinalities (Book↔BMS, bot↔Book, Book↔account/venue)

**bot↔Book / concurrency — FOUND (partial):**

> "`max_concurrent_live_bots=3`" — `qml-spec.md:151` (new-core risk-seat replacement for old capital slots).

A bot is **examined ONCE against a specific book contract** (`clash-report-bot-rating.md:19`,
`clash-report-backtest-replay.md:33` "certifying against a *specific book contract*, DEC-0055"),
i.e. bot binds to one book contract at certification. Old-vault bot carried a single
`account_id` + `account_mode` (LIVE|DEMO) (`bot-registry-lineage-spec.md:44`).

**Book↔BMS cardinality: NOT FOUND.** **Book↔account/venue (may one Book bind accounts at several
venues?): NOT FOUND** — the only "venue" token in corpus is `commission_per_lot` "(venue rate
schedule)" in the fill simulator (`backtest-engine-spec.md:57`), unrelated to binding. Cross-book
capital cap is deferred: "Exposure Desk v2 / cross-book cap ... Matters only when book #2 exists.
One-book world: Exposure v1 suffices" (`gaps-commentary.md:18`; GAP-0008).

---

## Topic 4 — Lifecycle states / modes (LIVE/PAPER/BENCHED/STOOD_DOWN; enum location; seat-state vs book-mode)

**Old-vault BOT lifecycle state machine — FOUND, VERBATIM (UNRATIFIED, old layer):**

```
States (bot-registry-lineage-spec.md:54-61):
  POST_WF1        (pseudo-state, NOT a registry row — WF1 never registered bots)
  POST_WF2        (first registry state, old WF2 Stage I.0)
  PAPER_TRADING
  LIVE            phase: probation (Kelly-discounted; auto-flip to full on per-archetype
                         criteria e.g. N winning sessions + no CB fires)
                  phase: full (neutral multiplier)
  DEMOTED
  PAUSED          (reversible, slot released, lineage preserved)
  RETIRED         (terminal — no transitions out; revival = new BotSpec with retired bot as parent_id)
```

Allowed-transition matrix (`bot-registry-lineage-spec.md:63-72`), key edges:
`(none)→POST_WF2` (registration; Schema+Sandbox validators + CapabilitySpec pass) ·
`POST_WF2→PAPER_TRADING` · `PAPER_TRADING→LIVE(probation)` (promotion gate + **manual approval**) ·
`LIVE(probation)→LIVE(full)` (auto-flip) · `LIVE→DEMOTED` (CB second hit | WF3 hard trigger |
operator) · `DEMOTED→PAPER_TRADING` (rehab child success | daily rollover reinstatement) ·
`LIVE/PAPER→PAUSED` (operator) · `PAUSED→previous` (operator) · `*→RETIRED` (manual; DEMOTED also
auto when all rehab children fail).

Old-vault **mutable Live-State field** carrying mode: `account_mode` (LIVE | DEMO — **broker routing
source of truth**) (`bot-registry-lineage-spec.md:44`). Old tag set (`bot-registry-lineage-spec.md:130-133`):
`post_wf1, post_wf2, paper, demo, live-probation, live-full, decayed, paused, retired`.

**New-core re-anchor (GitBook layer, 2026-07-18):** "the whole machine maps onto Treasury cycles +
Exam certification + leash rungs — e.g. demotion→bench-to-paper, retirement→death condition/sunset
review; the state SET must be re-derived" (`bot-registry-lineage-spec.md:73-76`). New modes named
in corpus: **bench-to-paper** (leash rung) (`clash-report-alpha-decay.md:35`,
`clash-report-bot-rating.md:35`), **kill-line → paper until re-seed at cycle boundary** (DEC-0023)
(`clash-report-bot-rating.md:44-45`).

**BENCHED / STOOD_DOWN enums, seat-state vs book-mode split, which enum lives where: NOT FOUND** as
such — this corpus only has the old BOT state machine (above) plus new "bench-to-paper" phrasing.
The Book-mode enum and seat-state enum are not defined here.

---

## Topic 5 — Book versioning + compatibility (scalping-book-v2 = new Book, never inherits v1 ledger)

**NOT FOUND for Books.** No `scalping-book-v2` / book-versioning / ledger-non-inheritance statement
exists in this corpus. The only versioning discipline present is **BotSpec immutability**: "Immutable
after creation; mutation ⇒ NEW BotSpec, new `id` (UUID, never recycled), `parent_id` → progenitor"
(`bot-registry-lineage-spec.md:20-22`) and QML "additive versioning" for domain types
(`qml-spec.md:57`). No Book-level analogue is recorded.

---

## Topic 6 — Exit ownership (PRIMARY: bots own exits vs Book owns exits; forced exits; fast invalidation; dynamic SL/TP; position safety authority)

**This is the richest topic in my corpus.** Two primary sources: `sltp-authority-spec.md`
(old-vault UNRATIFIED extraction) and `clash-report-sltp-vs-book.md` (2026-07-18 GitBook-layer analysis).

### 6a. Old-vault SL/TP mandate — bots do NOT own exits (UNRATIFIED, oldest layer)

> "System-owned service managing the SL/TP lifecycle of every live position. Bots do not own,
> compute, or amend stops — they publish intent, then relinquish control. Rationale: one consistent
> asymmetric policy; uniform kill-switch overrides with no per-bot wiring; losers reach their FULL
> original stop to feed clean loss signals downstream." — `sltp-authority-spec.md:21-26`

### 6b. The asymmetric policy — VERBATIM (`sltp-authority-spec.md:28-48`)

```
TP: continuous trailing.
  Per tick, query continuation_prob [0,1] from the market-intelligence layer
  (never computed inside the Authority).
  Condition: unrealised_pnl_pips > original_risk_pips AND continuation_prob > CONTINUATION_THRESHOLD
  Action:    extension_pips = f(continuation_prob, unrealised_pnl_pips)
             (f in shared contract layer, monotonically increasing in continuation probability)
             new_tp = current_tp + extension_pips × direction_sign
  No hard TP cap — bounded only by the signal weakening.

SL: one-shot to breakeven at +1R.
  Trigger: unrealised_pnl_pips >= original_risk_pips AND sl_at_breakeven == false
  Action:  new_sl = entry_price + spread × direction_sign ; set flag
  NEVER reset for the life of the position (even from +3R reversal).
  Only a kill-switch override may impose a tighter stop.

P&L ladder: entry (SL/TP at originals) → +1R (SL one-shot to BE) → continued profit (TP extends)
            → reversal to BE (0R loss unit) → reversal past BE without BE activation (full 1R loss unit).

Rationale for full-stop losers [OLD-CB COUPLING — re-validate]: a wick-to-BE-then-reverse trade
must deliver an unambiguous 1R loss unit so breaker thresholds stay calibrated; trailing would
understate loss magnitude.
```

### 6c. Old-vault kill-switch override hierarchy — VERBATIM (`sltp-authority-spec.md:69-76`)

```
System-level, never per-bot; a priority gate above all SL/TP decisions.
  Tighten   — SL to tighter level (e.g. 50% of remaining distance to entry)
              [⚠️ TIGHTEN half-size is DEAD in the new core, DEC-0019 — must NOT survive as-is]
  Breakeven — SL to BE immediately regardless of P&L
  Flatten   — close all positions
All priority 0, pre-empting same-tick TP extensions/normal moves. No per-bot kill-switch setting exists.
```

Contracts (`sltp-authority-spec.md:52-66`): **AmendInstruction** `reason ∈ {BREAKEVEN, TP_EXTENSION,
KILL_SWITCH_OVERRIDE}`, `source: "sltp_authority"` (**always; never the bot**), `priority`
(kill-switch = 0, normal = 10); "Adapter processes in priority order; 0 supersedes all pending
regardless of queue" (`sltp-authority-spec.md:60-61`).

### 6d. The clash — new core has NO stop-management component (GitBook layer, 2026-07-18)

> "the new system has **NO stop-management component** — and that absence is not neutral. The book's
> money math silently assumes answers about stop behavior in at least three load-bearing places...
> they are a hole the book system is standing over." — `clash-report-sltp-vs-book.md:6-10`

> "**Nowhere**: who sets the stop, who may move it, whether TP trails, whether breakeven moves exist,
> what happens to open positions at rollover/sweep/kill-line. The words 'stop-loss' and 'take-profit'
> do not appear as owned behavior in any component page." — `clash-report-sltp-vs-book.md:29-32`

### 6e. Proposed resolution — "stop policy = money shape" + a Position Safety service (proposal, 2026-07-18)

> "**Stop policy is part of a book's MONEY SHAPE.** The charter's second slot is the constitutional
> home..." — `clash-report-sltp-vs-book.md:67-68`
> A single **Position Safety service** executes whatever policy the book declares (one implementation,
> per-book config); under ADR-0001 it "senses (MI continuation input, information-only per L6),
> **decides post-entry stop amendments**, executes via adapter; accounts nothing (journals via BMS
> Records...)" — `clash-report-sltp-vs-book.md:79-83`.

What **survives** as candidate grammar (`clash-report-sltp-vs-book.md:85-89`): one-shot-BE + never-reset
flag; full-stop losers; TP trail as f(continuation_prob) with hold-on-MI-timeout; WAL +
broker-reconciliation restart; amendment idempotency threshold; conservative fail-safe ("when in
doubt, do not widen risk"). What **dies** (`clash-report-sltp-vs-book.md:90-92`): TIGHTEN override
(DEC-0019); any notion the SL/TP service is globally uniform across books (DEC-0024);
CB-calibration rationale must be re-derived against `scalper_breaker_threshold` semantics.

### 6f. Forced exits already in the new leash chain — FOUND

> "**Leash chain** includes **hold-time force-flat** (a position-closing authority!) and classed kill
> switch (DEC-0037)." — `clash-report-sltp-vs-book.md:24-25`

Position-safety **failure modes** (conservative default, keep verbatim; `sltp-authority-spec.md:96-102`):
Broker unreachable → queue amendments, exp. backoff, keep tracking. MI timeout → hold last TP, never
widen, never close; SL monitoring continues. Kill-switch signal lost → maintain last-known state,
alert ops, **never infer a lift**. Restart → WAL + broker reconciliation before resuming. Unconfirmed
position → never tracked, never amended, alert emitted.

**Fast invalidation:** the *term* appears only in the checklist; my corpus's nearest referent is
**hold-time force-flat** + kill-switch Flatten. No organ named "fast invalidation" here.

---

## Topic 7 — Paper mode (bench-to-paper, paired demo bindings, duplicate-order prevention, live↔paper, evidence comparability)

**FOUND (partial):**
- **bench-to-paper is a leash rung** (`clash-report-alpha-decay.md:35`; `clash-report-bot-rating.md:35`
  "Paper-trading demotion → bench-to-paper leash rung").
- **kill-line → paper until re-seed at the cycle boundary** (DEC-0023) (`clash-report-bot-rating.md:44-45`).
- **Paper = frozen counterfactual diagnostic (L13)**, NOT a proving ground / comeback arena:
  > "paper mode is a **frozen counterfactual diagnostic** (L13) ... Paper is a morgue window, not a
  > comeback arena." — `clash-report-bot-rating.md:43-47`; restated `clash-report-alpha-decay.md:44-45`.
- **Redemption loop is structurally dead** (old paper→live comeback gone) (`clash-report-bot-rating.md:43-47`).
- **Paper/demo scored separately from the live rolling tier** (`dpr-prs-spec.md:57`).
- Old-vault `account_mode` LIVE|DEMO is broker-routing source of truth (`bot-registry-lineage-spec.md:44`).
- **Paper/live transition state machine is an OPEN load-bearing gap (GAP-0006):** "Paper mode touches
  the breaker (bench), kill-line (flip to paper), and the exam pipeline ... Needs ruling before coding
  the leash." — `gaps-commentary.md:16`.

**Paired demo bindings: NOT FOUND. Duplicate-order prevention: NOT FOUND.** (Nearest engineering
control anywhere in corpus is **amendment idempotency**, `sltp-authority-spec.md:91-94`, and
**Journal bridge idempotent on trade_id**, `qml-spec.md:97` — neither is a paper/demo duplicate-order
guard.) **Evidence comparability**: implied by exam/live parity (Topic 6e) but not stated for paper.

---

## Topic 8 — News protection (before/after windows, severity tiers, currency→instrument map, open-position behavior, overrides)

**FOUND only as signal fields + a safety hook — NO quantified windows/tiers:**
- MarketIntelligenceSnapshot carries `news_state` + `news_currency_scope` (signal-only):
  `qml-spec.md:80`.
- Old-vault runtime **news safety hook** exists among the nine priority-ordered hooks:
  "session, session_warmup, kill_switch, **news**, dpr(two-strike), spread(sqs_hard_block),
  regime(HIGH_CHAOS), feature_quality, concurrent_slot" — `qml-spec.md:122`.
- Backtest fill sim `rejection_probability` "(per symbol, e.g. **news spread-widening**)" —
  `backtest-engine-spec.md:58`; historical news events are an optional replay input
  (`backtest-engine-spec.md:95-96`).

**Before/after windows in minutes: NOT FOUND. Event severity tiers: NOT FOUND.
Currency→instrument mapping: NOT FOUND** (only the field name `news_currency_scope`).
**Open-position behavior on news: NOT FOUND. Overrides: NOT FOUND.**

---

## Topic 9 — SQS / spread-quality sensing (formula, inputs, thresholds, cadence, hysteresis, WHY)

**FOUND as fields + a blocking hook — NO formula:**
- MarketIntelligenceSnapshot fields (signal-only, per-symbol/tick): `current_spread`,
  `spread_quality`, **`sqs_hard_block`**, `microstructure_quality`
  (NATIVE_HIGH/PROXY_HIGH/DEGRADED/DISABLED), `proxy_orderflow_signal` — `qml-spec.md:79-81`.
- **WHY it existed / how it acts:** it is a **spread safety hook that BLOCKS**: hook name
  "**spread(sqs_hard_block)**" in the priority-ordered runtime (`qml-spec.md:122`); "MI ... SQS —
  information inputs ONLY; replayed risk authority owns trade-control" (`backtest-engine-spec.md:42`).
  So SQS = spread-quality sensor whose hard-block variant gates entry; the block decision is a
  door/hook, the *sensing* is information-only from the MI layer.

**Formula / numeric thresholds / cadence / hysteresis: NOT FOUND.** No SQS math is published anywhere
in this corpus.

---

## Topic 10 — Kill switch / KSA (authority model, scopes, escalate-only + human de-escalate, effect vocabulary, adapter interaction)

**FOUND (substantial, mixed layers):**
- **Five levels stay; escalate-only + human de-escalation:** "Five levels stay (DEC-0043); TIGHTEN
  dead (DEC-0019); REGION_SHIFT rotation dead (DEC-0021); **escalate-only, A1 de-escalation (L8)**;
  Prune enum + triggers" — `qml-spec.md:156`. (The five level names are NOT enumerated in my corpus —
  DEC-0043 is only referenced.)
- **KSA is a door, enforced by the adapter:** door #7 (`clash-report-sltp-vs-book.md:15-17`;
  `qml-spec.md:159`); "post-doors, the book sends platform-blind commands; the adapter enforces KSA
  effects" (`clash-report-sltp-vs-book.md:26-27`); "KSA effects enforced by the adapter AND the leash's
  hold-time force-flat" (`clash-report-sltp-vs-book.md:56-58`).
- **Outage default:** old-vault Kill-Switch bridge "outage defaults ORANGE, never GREEN"
  (`qml-spec.md:97`); kill-switch signal lost → maintain last-known state, never infer a lift
  (`sltp-authority-spec.md:100-101`).
- **Old-vault effect vocabulary (UNRATIFIED):** Tighten / Breakeven / **Flatten (close all positions)**,
  all priority 0 (`sltp-authority-spec.md:70-76`).
- **KSA trigger→level matrix is an OPEN safety-critical gap (GAP-0015):** "Especially connectivity +
  unknown-state faults. Small matrix, high stakes; needs your ruling before the adapter/KSA code path
  is written." — `gaps-commentary.md:25`.
- Old-vault adapter extension point signatures: `place_order`, `amend_position_sltp`,
  `close_position`, `deal_close_hook` (`qml-spec.md:128-129`).

**Scopes (pair/Book/account/venue/global): NOT FOUND** as an explicit scope ladder.
**Effect vocabulary suspend-new / drain / close_all: PARTIAL** — only old-vault "Flatten = close all
positions"; `suspend-new` and `drain` do not appear in my corpus.

---

## Topic 11 — Correlation ledger / correlation rules (computed vs enforced)

**FOUND (thin):**
- **Cohort correlation is certified at exam as a condition of entry:** "the Exam certifies a footprint
  (measured Lbar, fire-rate bands, regime-conditional EV, **cohort correlation**) as the condition of
  entry" — `clash-report-alpha-decay.md:61-62`.
- Correlation math tooling is boxed: Riskfolio-Lib is permitted ONLY in the WF3 dead-zone pool-cleaning
  + DPR drawdown calculators, "never hot path, never sizing authority, never execution/lifecycle"
  (`alpha-decay-spec.md:11-12`, `alpha-decay-spec.md:52-56`).
- Enforcement analogue is the **exposure-ledger door** (#6) + Exposure Desk; cross-book cap deferred to
  GAP-0008 (`gaps-commentary.md:18`).

**Computed vs enforced split: NOT clearly stated. A "correlation ledger" as a named artifact:
NOT FOUND.**

---

## Topic 12 — Money ladder + R (FORM-0004, FORM-0006, variable meanings/units, seat/offer/take, treasury seed-to-cap+sweep, distinct capital concepts)

**Seat-offer formula — FOUND, VERBATIM (three consistent occurrences):**

> "`offer_per_seat = D/(B·b·Lbar)` prices seats off the bot's characteristic loss." —
> `clash-report-sltp-vs-book.md:47`
> "risk seats sized by budget math (`offer = D/(B·b·Lbar)`)" — `clash-report-bot-rating.md:32`
> "`offer_per_seat=D/(B·b·Lbar)`; `take=min(offer, trust-bounded cost-aware Kelly)`;
> `max_concurrent_live_bots=3`; Treasury cycles + Exposure Desk" — `qml-spec.md:151`

This matches the checklist's FORM-0004 shape `offer_R_usd = D/(B·b·Lbar)`. **Take mechanic:**
`take = min(offer, trust-bounded cost-aware Kelly)` (`qml-spec.md:151`).

**Variable meanings/units as recorded in MY corpus (I record only what is cited):**
- **Lbar** = `registry:scalper_mean_loss_r`, **`kind: measured`, measured per bot at exam**
  (`clash-report-sltp-vs-book.md:20-21`); i.e. the bot's characteristic/mean loss expressed in **R**.
  "Lbar measured" also `dpr-prs-spec.md:69`, `clash-report-alpha-decay.md:61`.
- **D, B, b** — appear ONLY inside the formula; **their individual definitions/units are NOT spelled
  out anywhere in this corpus.** Contextual (NOT a ruling — recorded, not decided): "daily budget" is
  door #4 and budget-drain is DEC-0031 (`clash-report-sltp-vs-book.md:15,22`); `scalper_breaker_threshold`
  = consecutive stop-outs to paper, DEC-0032 (`clash-report-sltp-vs-book.md:20-21`). The corpus does
  **not** bind D/B/b to those names.
- **FORM-0001..0005** are referenced as the "money ladder" set (`clash-report-backtest-replay.md:43`,
  `:87`) but only FORM-0004's shape is quoted.

**FORM-0006 (`R_max_usd <= B·b·Lbar`): NOT FOUND.** R_max appears only as **door #3 name**
("R_max", `clash-report-sltp-vs-book.md:15`; `sltp-authority-spec.md:11`; `qml-spec.md:159`) — no
formula for it is quoted here.

**Treasury cycle / seed-to-cap / sweep — FOUND (GitBook layer):**
> "Treasury cycle (**seed→cap, kill-line→paper until re-seed; no top-up DEC-0020; no inter-cycle
> compounding**)" — `qml-spec.md:155`
> "treasury cycle (money resets at rollover; **ratchets between cycles**)" — `clash-report-bot-rating.md:23`
> "**sweep at rollover, re-seed at cycle boundary**, Sunday committee" — `clash-report-alpha-decay.md:53-54`
> "per-book cycle economics (**swept cash per seed** — the scalper book's own headline metric)" —
> `clash-report-bot-rating.md:84`
> "L4: unclaimed/freed budget is **never redistributed in-cycle**" — `clash-report-bot-rating.md:48-50`

**Distinct capital concepts present:** seed, cap, daily budget (D / door #4), offer-per-seat, take,
risk seat, R (unit), Lbar (measured loss in R), swept cash. **ρ refund-reserve** is a separate
Treasury concept: `refund_reserve ≈ ρ·N_cycles_month·S` (**FORM-0008**), ρ = refund-reserve
coefficient from ENH-0002, "unestimable before live data" (`gaps-commentary.md:17`).

---

## Topic 13 — Stop-out (definition; breakeven-exit ambiguity; consecutive-stop-out counter B=2)

**Breakeven-exit ambiguity — FOUND, this is a headline finding (GitBook-layer, 2026-07-18):**

> "The breaker counts 'stop-outs' — but **stop policy DEFINES what a stop-out is.** Under the old
> asymmetric policy, a position that reached +1R exits at breakeven (a 0R 'BE-out'), while true losers
> exit at the full original stop (1R). Question the new docs cannot answer: *does a breakeven exit
> count toward `scalper_breaker_threshold`?* If yes — benching accelerates wildly... If no — the
> one-shot-BE design quietly reduces breaker sensitivity... **This must be a ruling, not an
> inheritance.**" — `clash-report-sltp-vs-book.md:36-45`

Decision point D2 recommends (not a ruling): "do BE-outs count toward the breaker threshold?
(Recommend: **no** for the scalper book — count full stops only, keep BE-outs as a separate measured
metric ...)" — `clash-report-sltp-vs-book.md:97-100`.

**Consecutive-stop-out counter:** `registry:scalper_breaker_threshold` = "**consecutive stop-outs to
paper** (DEC-0032)" (`clash-report-sltp-vs-book.md:20`, `:19` "benches after consecutive stop-outs").
**The specific value B=2 is NOT stated in my corpus** — the counter exists and is named; its numeric
threshold is not quoted here. (Old-vault analogue: "CB second hit" / "two-strike dpr hook",
`bot-registry-lineage-spec.md:69`, `qml-spec.md:154` — old CB, dead/replaced.)

---

## Topic 14 — Alpha-decay evidence classes / 'the Book sets the bar' / qualification / exam certificates / certified footprint

**FOUND, rich.**

**Old-vault four evidence classes — VERBATIM (`alpha-decay-spec.md:26-34`):**
```
1. Rolling CB-fire density  — circuit-breaker fires per rolling window (cb_hits_in_window,
                              reset at daily rollover).
2. MAE/MFE drift            — shift over time in max-adverse / max-favorable excursion distributions.
3. DPR drawdown context     — from the rolling performance stream.
4. Regime/session overlays  — performance conditioned on market regime and session window.
```
Explicit hole: "**No formula, weights, lookback lengths, or numeric thresholds are published anywhere
in the vault.**" (`alpha-decay-spec.md:36-39`).

**New-core cleaner decay definition — VERBATIM (GitBook layer, 2026-07-18):**
> "**Alpha decay = sustained, measured divergence of a bot's live footprint from its certified
> footprint, and/or measured approach toward its charter's death condition.**" —
> `clash-report-alpha-decay.md:66-68`

**Certified footprint / 'the Book sets the bar':** "the Exam certifies a footprint (measured Lbar,
fire-rate bands, regime-conditional EV, cohort correlation) as the condition of entry"
(`clash-report-alpha-decay.md:61-62`); certification "against a *specific book contract* (DEC-0055)"
gating only on **edge-after-cost + non-fiction (DEC-0036)** (`clash-report-backtest-replay.md:32-33`;
`clash-report-bot-rating.md:19-20` "everything else is measured input, not judged input —
DEC-0036/0055"). Live drift metrics proposed: "live Lbar vs exam Lbar; live fire-rate vs certified
bands; live regime-conditional EV vs certified EV" (`clash-report-bot-rating.md:82-83`;
`clash-report-alpha-decay.md:82-84`).

**Old DPR composite (the buried qualification metric) — VERBATIM (`dpr-prs-spec.md:18-34`):**
```
Composite score [0,100], six weighted dimensions:
  1 Profitability          25%  Net P&L as % of risk deployed, fee-adjusted
  2 Consistency            20%  Stdev of per-trade returns vs mean; low dispersion scores high
  3 Drawdown Pressure      20%  Inverse of max intra-session drawdown vs equity at session open
  4 Fee Efficiency         10%  Gross profit / (total fees + slippage)
  5 Regime-Relative Edge   15%  Excess return vs null strategy of same archetype in same regime
  6 Session-Mix Performance 10% Win rate weighted by session difficulty (premium heavier)
Tiers: 80–100 T1 (elite) · 50–79 T2 (acceptable) · 0–49 T3 (underperformer; consecutive T3 → breaker eval)
```
**Status: this composite is judged a DEC-0018 violation and buried** ("Six declared weights
(25/20/20/10/15/10) are precisely 'opinions wearing math'", `clash-report-bot-rating.md:38-41`;
`dpr-prs-spec.md:29` "DEC-0018 caution"). Survives only as **measured** dimensions, not weighted
composite (`clash-report-bot-rating.md:59-66`).

**Exam certificate contents: NOT quoted as a schema** — named contents only (Lbar, fire-rate bands,
regime-conditional EV, cohort correlation; edge-after-cost + non-fiction gates).

---

## Topic 15 — Book/BMS validation leads (how a NEW Book or BMS proves itself before carrying money)

**NOT FOUND for Book/BMS self-validation.** My corpus's validation machinery is **BOT-centric**:
- A bot is **examined once against a specific book contract** before intake
  (`clash-report-bot-rating.md:19`); gates = edge-after-cost + non-fiction (DEC-0036).
- Statistical battery (ratified in new-core registry): "WF 6mo IS / 1mo OOS, ≥200 OOS trades/window,
  OOS EV floor 0.15R, MC 1000 shuffles, PBO pass<0.25 / dead>0.50" (`clash-report-backtest-replay.md:66-69`;
  `backtest-engine-spec.md:85-87`).
- **A backtest is against a BOOK, not just a bot** (nearest Book-validation hook): "the new one must
  load a book profile ... a backtest is against a BOOK" (`clash-report-backtest-replay.md:50-52`,
  `:105`); Replay Service replays "book instance profile" + doors + money ladder + leash + KSA
  (`clash-report-backtest-replay.md:87-88`).

How a **Book itself** (or a BMS) proves itself before carrying money is not addressed in this corpus.

---

## Topic 16 — Same-tick priority (protective stops, Book force-flat, kill switch, fast invalidation, discretionary exits); no-overnight; hold limits; dead-zone (~45min handover)

**Same-tick close-authority priority — FOUND (both layers):**
- **Old-vault (UNRATIFIED):** kill-switch overrides priority 0 vs normal SL/TP moves priority 10;
  "0 supersedes all pending regardless of queue" (`sltp-authority-spec.md:60-61`); all KS levels
  priority 0 "pre-empting same-tick TP extensions/normal moves" (`sltp-authority-spec.md:75-76`).
- **New-core clash + recommendation (2026-07-18):** "Two authorities can now close positions —
  priority is undefined" between KSA effects (adapter), leash **hold-time force-flat**, and SL/TP
  amendments (`clash-report-sltp-vs-book.md:55-63`). Recommended ordering (D4, a recommendation, not a
  ruling): "**KSA ≥ force-flat ≥ stop amendments, adapter-enforced** (recommend; write it into the
  leash spec)" (`clash-report-sltp-vs-book.md:102-104`). "The old priority model is a good donor; it
  just has to be re-anchored onto leash rungs (and TIGHTEN is dead, DEC-0019...)"
  (`clash-report-sltp-vs-book.md:61-63`).
- Backtest replay ordering: "kill switch ... checked BEFORE SL/TP each bar (affects `close_reason`
  attribution)" (`backtest-engine-spec.md:41`); per-bar sequence (`backtest-engine-spec.md:60-66`).

**Hold limits / no-overnight — FOUND (partial):** the leash chain includes **hold-time force-flat**, a
position-closing authority (`clash-report-sltp-vs-book.md:24`, `:57`). This is the corpus's only
hold-limit organ. **An explicit "no-overnight policy" is NOT stated** — only hold-time force-flat.

**Position fate at kill-line/sweep boundaries — explicitly OPEN:** "D5. Position fate at
kill-line/sweep boundaries (old docs silent, new docs silent — genuinely new design)."
(`clash-report-sltp-vs-book.md:104-105`).

**Dead-zone (~45min session-handover no-trade): NOT FOUND with that meaning.** "Dead-zone" in my
corpus is the **WF3 slow-path batch window** for pool-cleaning, not a session-handover no-trade band:
"Dead-zone, slow-path workflow; triggers: `scheduled_dead_zone` or `manual_operator_request`"
(`alpha-decay-spec.md:11`); `dead_zone_sync_gate` D0 waits on schedule + data-sync
(`alpha-decay-spec.md:16`). No ~45-minute figure and no session-handover semantics appear.

---

## Topic 17 — Multi-currency (account numeraire, cross-account aggregation, FX conversion for risk math)

**FOUND (thin — pip conversion only):**
- Old-vault **PipProfile** (resolved from broker adapter symbol table, cached per position):
  `symbol`, `pip_size` (**0.0001 EURUSD, 0.01 USDJPY**), `contract_size`, `min_lot`; "**All internal
  math in pips; converted to absolute price on emit.**" — `sltp-authority-spec.md:63-66`.
- PositionIntent carries `account_equity_at_entry` (`sltp-authority-spec.md:55`).

**Account numeraire: NOT FOUND. Cross-account aggregation: NOT FOUND. FX conversion for risk math:
NOT FOUND.** The corpus does its sizing in **R** and its stop math in **pips**; no currency-of-record
or FX-to-numeraire conversion is described.

---

# CONTRADICTIONS

1. **Seven-doors tail rendering differs between two GitBook-layer citations (same date).**
   `clash-report-sltp-vs-book.md:15-17` lists "...breaker → exposure ledger → **KSA → adapter**"
   (adapter as a terminal enforcement step after the 7th door), whereas `qml-spec.md:159` lists the
   7th door as "**kill switch**" and stops (adapter not in the door list). Not a substantive conflict —
   adapter is the enforcement layer *behind* door #7 (`clash-report-sltp-vs-book.md:26-27`) — but the
   two enumerations are not textually identical. Recorded, not resolved.

2. **Old-vault "Canonical v1.0" self-labels vs their extraction status.** Every `*-spec.md` source
   page calls itself "Canonical Spec v1.0"; every extraction explicitly strips that authority
   ("carries no authority now" / "UNRATIFIED baseline") (`sltp-authority-spec.md:6`,
   `dpr-prs-spec.md:5`, `bot-registry-lineage-spec.md:7`, `backtest-engine-spec.md:4`). Layer conflict
   resolved *inside the corpus itself* in favour of UNRATIFIED — but the label collision is on record.

3. **Old-vault SL/TP asymmetric policy vs new-core "no uniform SL/TP service" (DEC-0024).** The
   old-vault mandate asserts "one consistent asymmetric policy" system-wide, no per-bot wiring
   (`sltp-authority-spec.md:23-24`); the clash report rules that a globally-uniform SL/TP service is
   dead under DEC-0024 — policy must be per-book money-shape (`clash-report-sltp-vs-book.md:91`,
   `:70-76`). Direct old-vs-new contradiction; new core wins per the report's own precedence.

4. **BE-out stop-out ambiguity is an unresolved fork, not a fact.** Whether a breakeven exit counts
   toward `scalper_breaker_threshold` is explicitly undecided; both branches change book behaviour and
   neither is written down (`clash-report-sltp-vs-book.md:36-45`). Flagged so downstream does not
   mistake the D2 *recommendation* ("no", `:97-100`) for a ruling.

---

# NOT-FOUND LIST (checklist topics with no evidence in THIS corpus)

- **Topic 1 (part):** CT-BOOK-01/02/03 verbatim field schemas — only the seven doors + charter-slot
  references are present.
- **Topic 2 (part):** CT-BMS-* verbatim field schemas — only boundary rulings (DEC-0045/0046, four
  desks).
- **Topic 3 (part):** Book↔BMS cardinality; Book↔account/venue multi-venue binding.
- **Topic 4 (part):** BENCHED / STOOD_DOWN enums; the seat-state vs book-mode split; which enum lives
  where (only the old BOT state machine + "bench-to-paper" phrasing exist).
- **Topic 5 (whole):** Book versioning / compatibility / `scalping-book-v2` / ledger non-inheritance —
  no Book-level analogue (only BotSpec immutability).
- **Topic 8 (most):** News before/after windows (minutes); severity tiers; currency→instrument map;
  open-position behavior; overrides — only `news_state`/`news_currency_scope` fields + a news hook.
- **Topic 9 (part):** SQS formula, inputs, thresholds, cadence, hysteresis — only the fields
  `spread_quality`/`sqs_hard_block` + the blocking hook.
- **Topic 10 (part):** Explicit scope ladder (pair/Book/account/venue/global); the five KSA level
  names (DEC-0043 referenced, not enumerated); `suspend-new` / `drain` effect vocabulary.
- **Topic 11 (most):** A named "correlation ledger"; the computed-vs-enforced correlation split (only
  cohort-correlation-at-exam + Riskfolio boxing).
- **Topic 12 (part):** FORM-0006 (`R_max_usd <= B·b·Lbar`); individual definitions/units of D, B, b
  (only Lbar defined; only FORM-0004's shape quoted).
- **Topic 13 (part):** The specific value **B=2** for the consecutive-stop-out counter (counter named
  via `scalper_breaker_threshold`/DEC-0032, value not quoted).
- **Topic 15 (whole):** How a NEW Book or BMS proves itself before carrying money (corpus is
  bot-certification-centric; nearest is "backtest is against a book").
- **Topic 16 (part):** Explicit no-overnight policy; the ~45-min session-handover **dead-zone**
  no-trade band ("dead-zone" here = WF3 batch window, different meaning).
- **Topic 17 (most):** Account numeraire; cross-account aggregation; FX conversion for risk math (only
  pip↔price conversion + `account_equity_at_entry`).
