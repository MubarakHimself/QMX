# 10 — DPR, PRS, and "benching": what they actually were

**Purpose.** Settle three half-remembered terms before the trading-node session: `DPR`, `PRS`, and "benched".
**Status.** Evidence dig. Everything below is *evidence needing fresh ratification*, in the standing authority order:
**current operator rulings > GitBook > legacy corpus.**

**Path legend used in citations**

| Prefix | Root |
| --- | --- |
| `GITBOOK:` | `https://elios-1.gitbook.io/qmx` (fetched live for this dig) |
| `REF:` | `C:\Users\Mubarak\Desktop\QMX\reference\` |
| `REC:` | `C:\Users\Mubarak\Desktop\QMX\.recovery\` |
| `OLD:` | `C:\Users\Mubarak\Documents\QMX\` (old corpus — **evidence only**, never a build source) |

---

## 1. In plain words

1. **PRS = Performance Rating *Service*.** The operator's "performance rating system" is right in substance, one word off. It was a standalone service that turned closed trades into a 0–100 score and a T1/T2/T3 tier. `OLD:raw\local-cleaned\2026-07-20-recovered-design-artifacts\dpr-prs-spec.md:3`
2. **DPR was the *rolling* output of that service** — a 10-session-window tier recomputed at daily rollover, used for the slow/strategic calls (demotion, decay response), as opposed to the instant per-trade "session tier" used for capital access now. `OLD:...\dpr-prs-spec.md:38-42`
3. **What "DPR" stands for is nowhere written down.** No source in any corpus expands the acronym. Do not let anyone invent one.
4. **DPR/PRS existed nowhere in the GitBook** — not as a page, not as a term. Verified against the live GitBook index. They live *only* in the old corpus and, in the recovery corpus, only inside **do-not-revive lists**. `REC:trading-node-delta\work\wiki-inventory.md:317`, `REC:backtesting-engine-retrieval\work\bmad-status.md:305`
5. **The operator's alpha-decay memory is half right.** PRS was its own service; **DPR was one of four evidence classes feeding alpha-decay sensing**, and the two were welded to the old circuit breaker. `OLD:...\clash-report-alpha-decay.md:5-9,15-19`
6. **"Benched" IS in the GitBook — prominently.** This is the one place the operator's recall is wrong. It is door 5 of the seven doors, rung 3 of the leash chain, and a value in the mode enum. `GITBOOK:/components/paper-mode-system`, `REF:05-trading-node-primer.md:104,187,197`
7. **The "maximum losing trades" memory is real, but sharper than remembered:** it is **`B` = 2 *consecutive stop-outs*** — consecutive, not cumulative; stop-outs, not losses. `OLD:wiki\registry\variables.md:23`
8. **Two different benchings must not be merged.** Legacy bench = rating-driven demotion with a paper *redemption loop*. Current bench = event-driven, rest-of-day, auto-reset. The redemption loop is structurally dead. `OLD:...\clash-report-bot-rating.md:42-47`
9. **Coming back from benched is fully defined in the current baseline** — automatically, at next open. Nothing else about paper/live movement is defined; it is `GAP-0006`.
10. **The alpha-decay *math* is gone.** Not misplaced — never written down. `REC:backtesting-engine-retrieval\work\bmad-status.md:298`

---

## 2. The reconstructed mechanism, claim by claim

### 2.1 PRS — the old Performance Rating Service

| Claim | Citation |
| --- | --- |
| Source document was the old vault's `06-performance-rating-service.md`, self-labeled "Canonical Spec v1.0" — a label the extraction says "carries **zero authority** now". | `OLD:...\dpr-prs-spec.md:3-4` |
| Its own header states: "The GitBook core has **NO** bot-rating mechanism… This spec is the only written record of that capability." Status: **UNRATIFIED baseline**. | `OLD:...\dpr-prs-spec.md:5-7` |
| Pipeline: consume `trade_close` events → compute composite score → map to tier → publish. | `OLD:...\dpr-prs-spec.md:11-13` |
| Old consumers, all four now gone: **slot auction, circuit breaker, paper-trading demotion, agentic selection/mutation targeting**. | `OLD:...\dpr-prs-spec.md:13-14` |

**Inputs — the composite score, [0,100], six declared weights** (`OLD:...\dpr-prs-spec.md:16-26`):

| # | Dimension | Weight | Definition as written |
| --- | --- | --- | --- |
| 1 | Profitability | 25% | Net P&L as % of risk deployed, fee-adjusted |
| 2 | Consistency | 20% | Stdev of per-trade returns vs mean; low dispersion scores high |
| 3 | Drawdown Pressure | 20% | Inverse of max intra-session drawdown vs equity at session open |
| 4 | Fee Efficiency | 10% | Gross profit / (total fees + slippage) |
| 5 | Regime-Relative Edge | 15% | Excess return vs null strategy of same archetype in same regime |
| 6 | Session-Mix Performance | 10% | Win rate weighted by session difficulty (premium heavier) |

Weights lived in shared-library contracts and were **hot-updatable**; sub-scores normalised to [0,100] before weighting (`OLD:...\dpr-prs-spec.md:27-28`). The extraction flags this itself as a **DEC-0018 violation** — declared weights are "opinions wearing math" (`OLD:...\dpr-prs-spec.md:28-29`, `OLD:...\clash-report-bot-rating.md:38-41`).

**Thresholds — the tiers** (`OLD:...\dpr-prs-spec.md:31-34`):
- **80–100 → T1** (elite)
- **50–79 → T2** (acceptable)
- **0–49 → T3** (underperformer)
- **"consecutive T3 triggered breaker evaluation"** — this is the single documented line linking the rating to benching.

**Two output streams** (`OLD:...\dpr-prs-spec.md:36-42`):
- **Session-tier (instantaneous)** — refreshed per trade-close, transient, never persisted, plus an authoritative session-end recompute from journal. Drove *tactical* decisions.
- **DPR (rolling)** — **10-session window, recomputed at daily rollover.** Drove *strategic* decisions: **demotion, decay response.**

**Mechanics** (`OLD:...\dpr-prs-spec.md:44-57`) — rolling tier = **modal tier across a capped 10-entry history**, tiebreak T1>T2>T3; `consec_t3` = leading contiguous T3 run; per-bot keys `prs:{bot_id}:scores`, `:tier_history`, `:rolling_tier`, `:consec_t3`, `:last_updated`; **daily reset at rollover** clears history and zeroes `consec_t3` but **carries the rolling tier forward** rather than blanking it; publish-subscribe with PRS never calling consumers; `<50ms` write-path latency target; idempotent `recompute(bot_id, session_window)` replay API; **paper/demo trades scored separately from the live rolling tier**.

**Timescale split — what each stream had power over** (`OLD:...\clash-report-bot-rating.md:13-17`): the instantaneous session-tier fed the **slot auction and the `dpr_multiplier`** — *capital access NOW*; the rolling 10-session DPR fed the **circuit breaker, WF3, and demotion** — *survival LATER*. "Capital chased merit tick by tick."

### 2.2 What happened on breach — legacy vs current

**Legacy path (dead).** Consecutive T3 on the rolling DPR triggered breaker evaluation; a bot could be **demoted to demo/paper**, its slot weight reduced (`reduce_weight`), or be **retired** (`OLD:...\dpr-prs-spec.md:33-34`, `OLD:...\clash-report-alpha-decay.md:15-19`). Critically: **"Demoted bots kept scoring on paper to win their way back — a redemption loop"** (`OLD:...\clash-report-bot-rating.md:16-17`), with rehab via mini-WF2 mutation while the parent sat on demo (`OLD:...\clash-report-alpha-decay.md:18-19`).

The legacy triage ladder was **four rungs, not one**, applied in the dead-zone batch by WF3 (`OLD:...\alpha-decay-spec.md:58-72`):

| Outcome | Trigger class | What happened | How the bot came back |
| --- | --- | --- | --- |
| `keep` | — | No thresholds crossed; recorded, nothing else. | n/a |
| `reduce_weight` | **soft** | Tagged `decayed` (a sub-tag of live), slot weight reduced, "on watch". | Next dead-zone window: **recovery → full weight**; continued decay → demote. |
| `demote_to_demo` | **hard** | Execution routed to demo. Described as *"same terminal effect as a **CB second strike**"*. | *"awaits re-promotion"* — mechanism not specified. |
| `retire` | **hard** (`WF3_PRUNE`) | Terminal. Also fires when all rehab children fail. | Only via **a new BotSpec with `parent_id`** — i.e. a descendant, not the bot itself. |
| `rehab_spawned` | — | Mini-WF2 handoff token (`decay_assessment_ref`, `trigger_metrics`, `parent_bot_id`, `rehab_priority`, `lineage_ref`, `opinion_ids[]`). | **"Demoted parent may re-enter via probation if a child rehabilitates it."** |

Two things to notice. First, **the legacy bench was not automatically time-limited** — it "awaited re-promotion" through a rating/probation process, which is exactly the redemption loop the current baseline kills. Second, the phrase **"CB second strike"** shows the old circuit breaker had a multi-strike escalation the current single-threshold breaker does not; no strike table survives.

**Current baseline path (ratified).** No rating anywhere in the chain:

| Element | What the baseline says | Citation |
| --- | --- | --- |
| Trigger | "After `registry:scalper_breaker_threshold` consecutive stop-outs, the affected bot benches to paper for the rest of the day and auto-resets at next open." DEC-0032. | `GITBOOK:/components/paper-mode-system` (live fetch); mirrored at `OLD:raw\online\qmx-gitbook\captures\2026-07-18T141659Z\pages\markdown\components\paper-mode-system.md:24` |
| Threshold value | `scalper_breaker_threshold`, symbol **`B` = 2**, unit `count`, kind `consecutive_stopouts`, owner `COMP-BOOK-SCALPER`, note "Consecutive stop-outs before bench-to-paper." | `OLD:wiki\registry\variables.md:23` |
| Window | **Intraday, resets daily.** Rest-of-day scope, auto-reset at next open. No multi-session window. | same as trigger |
| Where it sits | **Door 5 of the seven doors**: "Has this bot just lost too many in a row?" | `REF:05-trading-node-primer.md:104` |
| Also | **Rung 3 of the leash chain** ("bench-to-paper"), described as "the one paper transition that is actually ratified". | `REF:05-trading-node-primer.md:178,187` |
| Effect | Seat flips **LIVE → BENCHED**; BENCHED **behaves as paper**. | `OLD:_bmad-output\planning-artifacts\ux-designs\ux-QMX-2026-07-21\.working\sources-extract-wiki.md:87` |
| Return | **Automatic, at next open.** "Breaker bench-to-paper auto-resets at next open under DEC-0032." | `REF:05-trading-node-primer.md:197` |
| Everything else | "Other paper/live promotion, freeze, demotion, and return semantics remain **GAP-0006**." | `REF:05-trading-node-primer.md:197,315` |

**A quiet trap worth naming:** the same symbol **`B`** is *both* the breaker threshold *and* a divisor in the money ladder — `FORM-0004 offer_R_usd = D / (B * b * Lbar)` and `FORM-0006 R_max_usd <= B * b * Lbar` (`REF:05-trading-node-primer.md:102,122`). Changing the "how many losses before bench" number therefore **silently resizes every seat**. That coupling is in the baseline and does not appear to be commented on anywhere.

### 2.3 How it fed alpha-decay sensing

Old decay sensing was a **population problem** — a global pool of bots competing for slots, triaged in the "dead-zone" window because no auction ran then (`OLD:...\clash-report-alpha-decay.md:11-14`). Four evidence classes fed a typed decay score (`OLD:...\clash-report-alpha-decay.md:15-17`, restated at `OLD:wiki\attic\topics\alpha-decay-and-performance-analytics.md:35-40`):

1. rolling **circuit-breaker fire density** (`cb_hits_in_window`);
2. **MAE/MFE distribution drift**;
3. **DPR drawdown context** ← the PRS/DPR contribution;
4. **regime/session-conditioned performance overlays**.

Output branched into a **soft trigger** (`reduce_weight` — literally slot weight) and **hard triggers** (`demote_to_demo`, `retire`) (`OLD:...\clash-report-alpha-decay.md:17-19`). Riskfolio was restricted to dead-zone analysis and DPR drawdown support, never hot-path or sizing authority (`OLD:wiki\attic\topics\alpha-decay-and-performance-analytics.md:31`).

**Two of the four evidence classes reference machinery that no longer exists** — CB-fire density (the CB and its counter are gone; the analog is leash-event frequency, which is exactly the open `GAP-0012`) and DPR drawdown context (no DPR exists). The other two — MAE/MFE drift and regime/session overlays — survive cleanly as journal-derived measurements (`OLD:...\clash-report-alpha-decay.md:23-30`).

### 2.4 The disposition already recorded against these terms

Every recovery document that names DPR/PRS names them to **bury** them:

- "Do **not** carry old WF lifecycle, **DPR/PRS**, global pools/slots, paper redemption…" — `REC:trading-node-delta\work\wiki-inventory.md:317`
- Do-not-revive list: "**DPR/PRS merit ranking and tiers**; global bot pools and slot auctions; … paper-redemption/probation loops; continuous tiers" — `REC:backtesting-engine-retrieval\work\bmad-status.md:305`
- Attic ruling on `alpha-decay-and-performance-analytics.md`: *may remember* "read-only measurement should not acquire capital/lifecycle authority"; *must not rebuild* "**DPR/PRS ranks, global bot pool, continuous merit allocation, WF3 mechanics**" — `REC:trading-node-delta\work\wiki-inventory.md:253`
- Leash-map ruling on bench-to-paper: "The legacy circuit-breaker demotion path. GitBook narrows it to the Book breaker behavior. **Preserve current bot-seat semantics; do not revive DPR ranking, old trigger zoo, or slot-auction redemption.**" — `REC:trading-node-delta\recovery-lineage-addendum.md:139`
- Legacy capital slot: "its **DPR auction**, house-money inheritance, slot tables, and global pool **do not survive automatically**" — marked `DONOR`, not a current type — `REC:trading-node-delta\recovery-lineage-addendum.md:68`
- "attic/README: Ruled-out material — never build from this." — `REC:trading-node-delta\work\wiki-inventory.md:246`

### 2.5 What was proposed to replace them (unratified)

Both clash reports end with the same shape — **sense, never dispose**:

- **Performance Analytics Service** — read-model, zero authority, agent-callable. Reads BMS journals, veto ledger, exam certificates, treasury cycle events. Computes only measured, formula-registered metrics: realized-vs-certified footprint drift, fee efficiency, MAE/MFE distributions, per-book cycle economics. Serves Sunday Brief, sunset reviews (L16), leash-event context (GAP-0012). **Never ranks for capital, multiplies into sizing, or triggers any transition.** `OLD:...\clash-report-bot-rating.md:72-92`
- **A cleaner decay definition than the old system ever had**: *"Alpha decay = sustained, measured divergence of a bot's live footprint from its certified footprint, and/or measured approach toward its charter's death condition."* This is DEC-0018-clean because both sides of the comparison already exist as artifacts. `OLD:...\clash-report-alpha-decay.md:65-73`
- The DPR/PRS extraction's own re-anchor note agrees: old consumers map to **slot auction → seat/budget mechanics; circuit breaker → breaker door + leash; paper demotion → bench-to-paper rung**, and any revival is **new design**, "sensing only, never disposing." `OLD:...\dpr-prs-spec.md:65-72`

**Genuinely reusable engineering** (independent of the dead authority model): two-timescale thinking (event-fresh vs rollover-authoritative), capped-window rolling state, idempotent session-end recompute, publish-subscribe with consumers never polled, score-version retention. `OLD:...\clash-report-bot-rating.md:67-70`, `OLD:wiki\attic\topics\alpha-decay-and-performance-analytics.md:60-68`

---

## 3. Contradictions, flagged

1. **`BENCHED` is in two namespaces at once — unresolved.** GitBook `CT-BOOK-02` and `CT-BMS-02` share **one** enum `LIVE, PAPER, BENCHED, STOOD_DOWN` (`REF:05-trading-node-primer.md:197,414`). The later delta says this mixes two things and must be split: "V1 book modes are `LIVE`/`PAPER`; breaker `BENCHED` is **seat** state" (`REC:trading-node-delta\work\wiki-inventory.md:290`, `REC:trading-node-delta\trading-node-delta.md:72`, `REF:05-trading-node-primer.md:199`). The lineage addendum takes the delta's side: "`BENCHED` is a roster-seat state, not a Book mode" (`REC:trading-node-delta\recovery-lineage-addendum.md:66`). **Unratified. Needs an operator ruling before schemas are written.**
2. **Which decision owns the breaker threshold.** The registry row cites **DEC-0029** as `trigger_decision` for `scalper_breaker_threshold` (`OLD:wiki\registry\variables.md:23`), while every behavioural statement cites **DEC-0032** (`GITBOOK:/components/paper-mode-system`). Probably value-vs-behaviour, but it should be reconciled rather than assumed.
3. **"Stop-out" is not defined.** The breaker counts "consecutive stop-outs", but "a breakeven exit and a full original-stop loss are different outcomes… Whether a BE-out counts is undefined" (`OLD:wiki\topics\position-safety-and-sltp-authority.md:47`). This is open item **PE-3 stop-out taxonomy** (`REC:trading-node-delta\work\wiki-inventory.md:261`). **The breaker counter cannot be implemented correctly until this is ruled on.**
4. **"Bench" as breaker vs "bench" as decay response.** The decay clash report still lists "bench" among possible decay responses (`OLD:...\clash-report-alpha-decay.md:88-89`) while the current baseline treats bench-to-paper strictly as the breaker's event-driven rung. If decay sensing may ever *cause* a bench, that is a new authority grant, not a recovery.
5. **Three different things are called a "seat".** Roster seat (membership/lifecycle state), risk seat (the `offer`/`take` allocation channel), and legacy capital slot (persisted funded capacity with DPR auctions). `REC:trading-node-delta\recovery-lineage-addendum.md:121-131`. The GitBook uses "seat" throughout but **never defines it in the glossary** (`REF:05-trading-node-primer.md:392`).
6. **Operator recall vs evidence, stated bluntly.** The recall that "benched" was *not* in the GitBook is **incorrect** — it is baseline in three places. What genuinely came only from the recovery/old corpus is **DPR, PRS, tiers, the redemption loop, and the slot auction.** The two memories likely fused because the legacy circuit-breaker demotion and the current breaker bench share a name and an ancestor.

---

## 4. Genuinely unrecoverable — do not guess

| Item | Status |
| --- | --- |
| **What "DPR" stands for** | **Never expanded in any source.** Exhaustively searched GitBook, recovery corpus, and old corpus (including every `.tmp` working copy). The only token ever following "DPR" anywhere is "(rolling)". "Drawdown Pressure" is dimension 3 of the composite, *not* the acronym. Do not accept an invented expansion. |
| **Legacy re-promotion mechanism** | `demote_to_demo` "awaits re-promotion" — **who re-promoted, on what evidence, and after how long is never stated.** `OLD:...\alpha-decay-spec.md:65-66` |
| **The "CB second strike" ladder** | The old circuit breaker escalated in strikes; no strike count, window, or per-strike effect survives. `OLD:...\alpha-decay-spec.md:65-66` |
| **Soft/hard decay trigger thresholds** | *"No formula, weights, lookback lengths, or numeric thresholds are published anywhere in the vault."* `OLD:...\alpha-decay-spec.md:36-37,103` |
| **WF3 drawdown-decomposition submetrics** | Emitted an artifact per candidate; *"Sub-metrics of the decomposition: **unspecified** (gap)."* `OLD:...\alpha-decay-spec.md:55-56` |
| **The alpha-decay formula** | *"Alpha-decay math — Never written down — No retrieval possible; future design."* `REC:backtesting-engine-retrieval\work\bmad-status.md:298`. Confirmed independently: "No source supplies the decay formula, weights, lookback windows, thresholds, trigger criteria, or Riskfolio decomposition submetrics." `OLD:wiki\attic\topics\alpha-decay-and-performance-analytics.md:42` |
| **The `dpr_multiplier` transfer function** | Named as the thing that converted session-tier into capital access; the actual mapping is nowhere. `OLD:...\clash-report-bot-rating.md:14` |
| **Slot-auction mechanics** | Named repeatedly as a DPR consumer; no auction rules, bid model, or clearing procedure recovered. |
| **How many consecutive T3s triggered breaker evaluation** | The spec says "consecutive T3 triggered breaker evaluation" but **never states the count**. `OLD:...\dpr-prs-spec.md:33-34` |
| **Session difficulty weights** | Listed as a PRS data dependency; values never recorded. `OLD:...\dpr-prs-spec.md:62-63` |
| **Non-breaker return-to-live** | Not lost — deliberately open as **GAP-0006**. `REF:05-trading-node-primer.md:315` |
| **Leash-event frequency bands** | Open as **GAP-0012**; `chorus_expected_frequency_rule` value is `null`. `REF:05-trading-node-primer.md:188` |

---

## 5. Questions for the operator — trading-node session

Each carries a recommendation first, then a plain yes/no.

**Q1. Recommendation: YES, keep it buried.**
The old scoring service (PRS) and its rolling rank (DPR) rated every bot 0–100 using six weights someone chose by opinion, and that rank decided which bots got money. The current design deliberately has no such thing: a bot is examined once at the front door, then governed by rules, not by a running score.
**Do you confirm the 0–100 score and the T1/T2/T3 tiers stay dead, and are not rebuilt in the trading node?**

**Q2. Recommendation: YES, benching is exactly this and nothing more.**
Today's benching is simple: two losing exits in a row and that bot stops trading real money for the rest of the day, then automatically starts again at the next market open. No score, no appeal, no earning its way back early.
**Do you confirm that this — two in a row, rest of day, automatic return next morning — is the whole of benching for the build?**

**Q3. Recommendation: YES, split them.**
Right now one list of words is doing two jobs: it describes both what a *book* is doing (live or paper) and what one *bot's seat* is doing (live or benched). The recovery work says these are different things wearing the same label, and mixing them will bite when the data is designed.
**Do you agree the book's state and the bot's seat state become two separate things, so "BENCHED" only ever describes a bot?**

**Q4. Recommendation: YES, rule on it now — it blocks the build.**
The breaker counts "two stop-outs in a row", but nobody ever wrote down what counts as a stop-out. If a trade is moved to breakeven and then closes flat — no money lost — does that count as one of the two? The counter cannot be built until you answer.
**Should a breakeven exit (no loss taken) count toward the two?**

**Q5. Recommendation: YES, be aware — it is a real coupling, not a detail.**
The number "2" is used twice in the baseline: as the bench threshold *and* as a divisor in the formula that decides how much money each trade gets. Changing 2 to 3 to make benching less trigger-happy would also silently shrink every position size.
**Do you want that double-duty separated into two numbers, so bench-sensitivity and trade-sizing can be tuned independently?**

---

## 6. Sources consulted

**Live GitBook** — index and `/components/paper-mode-system` fetched during this dig.

**Recovery corpus** (`C:\Users\Mubarak\Desktop\QMX\.recovery\`)
`trading-node-delta\recovery-lineage-addendum.md` · `trading-node-delta\trading-node-delta.md` · `trading-node-delta\restart-handoff.md` · `trading-node-delta\work\wiki-inventory.md` · `trading-node-delta\work\bmad-supplement.md` · `trading-node-delta\work\gitbook-baseline.md` · `backtesting-engine-retrieval\work\bmad-status.md` · `backtesting-engine-retrieval\restart-handoff.md` · `backtesting-engine-retrieval\recovered-backtesting-engine.md`

**Current reference** — `C:\Users\Mubarak\Desktop\QMX\reference\05-trading-node-primer.md`

**Old corpus** (`C:\Users\Mubarak\Documents\QMX\`, evidence only — matched regions read, not whole files)
`raw\local-cleaned\2026-07-20-recovered-design-artifacts\dpr-prs-spec.md` (primary definitional source) · `...\alpha-decay-spec.md` · `...\clash-report-bot-rating.md` · `...\clash-report-alpha-decay.md` · `...\clash-report-sltp-vs-book.md` · `wiki\attic\topics\alpha-decay-and-performance-analytics.md` · `wiki\registry\variables.md` · `wiki\topics\position-safety-and-sltp-authority.md` · `raw\online\qmx-gitbook\captures\2026-07-18T141659Z\` (GitBook snapshot) · `_bmad-output\planning-artifacts\` (epics, PRD, UX extracts — corroboration only)

**Note on the old corpus.** `dpr-prs-spec.md` is an export of an old-vault file self-labelled "Canonical Spec v1.0". That label carries **zero authority** — the export says so itself on line 4. It is quoted here as the only surviving written record of a capability that was deliberately removed, not as a specification to build from.
