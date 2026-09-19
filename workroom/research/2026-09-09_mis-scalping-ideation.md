# MIS scalping ideation brief

> **Status:** research / planning only. Not architecture. Not implementation. Not STRATS population.
> **Date:** 2026-09-09
> **Feeds:** later BMAD sitting for Epic 30 Story 30.1 (`regime_classifier_v1` design), not a factory lane and not a docs mutation.
> **Copies:** `workroom/research/` (canonical) and `.hermes/plans/` (plan-skill location).

**Goal:** Put MIS in the shoes of a professional scalper: what regime/context must exist *before a bot is even allowed to look for a setup* — then map that onto QMX's ratified seam, not onto an imagined intelligence bus.

**Architecture (this artifact):** evidence-backed ideation. QMX law is the authority for what MIS *is*. MQL5 articles are method evidence only (vendor platform is not a commitment). Ideas are hypotheses. No edge is claimed. No Book sizing is designed.

---

## How to read this

Four separations, from the trading-strategy knowledge-engineering skill:

1. **Evidence vs interpretation.** Quotes and catalog facts are evidence. Vocabulary proposals, field-mapping, and sitting questions are interpretation.
2. **Primitive vs role.** Autocorrelation, BOCPD run-length, GARCH variance, session hour, spread ratio are primitives. In QMX they are *filters / coordinates / readiness*, never bot triggers.
3. **Source strategy vs runtime governance.** MQL5 EAs that switch playbooks or size from a regime label are source claims. QMX already assigns activation/block to the Book door and KSA; MIS never talks to bots (DEC-0204).[1][2]
4. **Candidate vs result.** Every idea family below is untested relative to QMX examination. Vendor backtests are not certificates.

**Non-goals (hard):** no code; no snapshot schema mint; no STRATS pages; no Book sizing; no claim that a regime label has an edge; no git-add of the MQL5 corpus; no hit on mql5.com origin.

---

## 1. MIS as-ratified vs as-imagined

### 1.1 As ratified (current `docs/` law)

MIS V1 is a **seam**, not a library and not a model runtime.[2][5]

- Compute-once, versioned, immutable per-instant **signal snapshot**, schema format-versioned, in-process, rule-based deterministic labelers.[2]
- Closed consumers: **Book door and KSA only**. Bots never consume the snapshot; QL-7 callbacks receive only declared footprint evidence.[1][2]
- SQS is a **separate** block-only CT-16 configured producer (DEC-0153). It reaches the door **only inside the snapshot**, so one instant carries exactly one SQS value.[1][2]
- SQS V1: historical session-window spread ÷ live spread; 1 is baseline; undefined/stale/refused means hard block; SQS never sizes, never authorizes, never blocks itself; V1 blocks only.[1]
- Explicit snapshot payload in current glossary/TN-19: per-instrument SQS score and hard-block; `feed_state` `live | degraded | dead`; `degraded_sensors`; labeler version stamps; readiness `ok | not_ready | unavailable | stale | refused`.[1][2]
- Producers read the world room **as of the slice frontier**, never wall-now; cannot-bound ⇒ `not_ready`.[1]
- Freshness bound is the Book's `registry:decision_freshness_bound`; past it is stale-evidence refusal. Until a live-path rung baseline exists, every labeler is **heavy by default**.[1][2]
- Shadow-lane seam is **V1 node work** (candidate role, separate `shadow_composition_fp`, comparison read model that gates nothing). Wiring a shadow output into a governed consumer refuses to boot.[2]
- **No trained model is bound in V1.**[2][5]
- Training/models are **GAP-0051 / Epic 30**, last node epic, offline operator-run script, never on the trading VPS, never on the decision path.[3][4]
- Catalog of eight labelers (DEC-0262): six rule-based — identity, spread-state, gap-event, feed-state, SQS, degraded-sensors; one fitted — `liquidity_stress_v1` (CPU quantile); one trained — `regime_classifier_v1` with **no** ratified model family, hyperparameters, label-generation method, or training location.[1][3]
- Recovered candidates **Kronos, HMM, BOCPD, MS-GARCH carry no authority until fresh ratification**. They are not implemented.[1][3][7]
- Protection windows (`news`, `daily_dead_zone`, `session_handover_buffer`) are **CT-31 / AD-38**, not MIS. They are calendar-derived and **absent for 24/7 markets**. They block new entries only (L39).[1]
- KSA trigger class `scheduled_news` is KSA, not a MIS label.[1]

### 1.2 As recovered from the old GitBook (historical, not the live contract)

The published GitBook CT-MIS-01 listed required fields `pair`, `resolution`, `snapshot_version`, `spread_state` (`normal|elevated|extreme`), `gap_event`, `liquidity_stress`, `feed_state` (`fresh|stale|dead`), `sqs_score`, `sqs_hard_block`, `degraded_sensors`, and optional `regime` (`trend|range|chaos`) plus `regime_confidence`.[6]

That is **recovered baseline**, useful as a field inventory. It is not DEC-0204. Drift that matters:

| Topic | GitBook / old corpus | Current ratified docs |
|---|---|---|
| Consumers | Book, KSA, and (in some recovered drafts) manifest-bounded bots | Book door + KSA **only**; bots never[1][2] |
| `feed_state` enum | `fresh \| stale \| dead`[6] | `live \| degraded \| dead`[1] |
| `regime` | optional `trend \| range \| chaos`[6] | undesigned `regime_classifier_v1`; not bound in V1[1][3] |
| SQS | named on the snapshot, semantically undefined in GitBook[6] | DEC-0153 block-only CT-16, snapshot-only delivery[1] |
| Trained models | implied live MIS-Live | not bound; last epic; recovered families unauthorized[3] |

### 1.3 As imagined (operator dump, prior research, vendor articles)

**Operator / tracker intent (not law):** old stack named Kronos (time-series) + BOCPD as candidates to re-ratify at an MIS session.[8] DEC-0262 already recorded those names as unauthorized recovered candidates, plus HMM and MS-GARCH.[1]

**Prior research `workroom/research/08-mis-ml-regime-models.md` (2026-08-17) is interpretation**, not a sitting. It argues five families (HMM / jump models / change-point / GARCH / clustering), the smoothing look-ahead trap, freeze-and-ship rather than online retrain, and regime as a **risk filter not a direction predictor**.[9] Useful as a critique of vendor APIs. It also says "Books and bots read that answer" — that sentence is **stale relative to DEC-0204** and must not be copied into a sitting.[9][2]

**MQL5 vendor pattern (method evidence):** almost every regime article *identifies* a state and then *lets an EA switch strategy or size*.[12][13] That second half is exactly what QMX forbids MIS to do. The first half is the scalper-context question.

**This brief's imagined target (operator intent, not yet ratified):** market-regime identification that QMX can use to **activate/block strategy classes** (choppy vs trend vs news vs dead) still via Book door / KSA, never piping MIS into bots. Crypto spot may become first live market; FX later. Keep the seam asset-agnostic; split FX-session features from 24/7.

### 1.4 One-line correction

Imagined MIS = a smart feed that tells bots what to trade.
Ratified MIS = a compute-once snapshot that tells **doors** whether the market is even eligible, and later (Epic 30) may add a **shadowed, unauthorized-until-ratified** regime label for those same doors.

---

## 2. Scalper-need list mapped onto snapshot fields

A professional scalper does not start with a setup. They start with: *is it even legal to look?*

**Interpretation:** map those questions onto QMX layers. Do not invent Book responses. "NEW" means a sitting would have to mint a snapshot field or a labeler output; it is not a license to mint one here.

| # | Scalper question (before any setup) | QMX home today | Snapshot field | Status |
|---|---|---|---|---|
| S1 | Is the feed honest / live / the one we pinned? | MIS labelers `feed-state`, `identity`, `degraded-sensors` | `feed_state`, `degraded_sensors`, identity stamps, readiness[1][2] | **Already in seam** |
| S2 | Can I get in and out at a cost that is not suicide? | SQS V1 + cataloged `spread-state` | `sqs_score`, `sqs_hard_block`; GitBook also had `spread_state`[1][6] | **SQS already in seam.** `spread_state` is cataloged as a V1 rule-based labeler but is **not named** in the current DEC-0204 payload list — Epic 26 owes the fold, not Epic 30. |
| S3 | Did price just gap / jump? | cataloged `gap-event` | GitBook `gap_event`[6] | **Cataloged V1 labeler** (Epic 26), not a new trained field |
| S4 | Is liquidity thin or stressed vs this instrument's own history? | fitted `liquidity_stress_v1` | GitBook `liquidity_stress`[6] | **Cataloged fitted V1** (Epic 26). Quantile of realized stress, not a GARCH forecast. |
| S5 | Are we inside a scheduled news window for this instrument? | CT-31 `news` + KSA `scheduled_news`; Forex Factory sole V1 source | none on MIS snapshot | **Other authority. Do not duplicate in MIS.** Calendar fact, not a statistical class. |
| S6 | Is this a daily dead zone or session handover? | CT-31 `daily_dead_zone`, `session_handover_buffer` | none | **Other authority. FX-session-specific; absent for 24/7.**[1] |
| S7 | What *kind* of market is this — chop, trend, violent, quiet? | undesigned `regime_classifier_v1`; GitBook optional `regime` `trend\|range\|chaos`[1][6] | `regime` + `regime_confidence` (historical optional) | **NEW for Epic 30 design** (the only trained labeler). Operator vocabulary `choppy vs trend vs news vs dead` **does not match** GitBook `trend\|range\|chaos` and **must not swallow** S5/S6. |
| S8 | Did the world *just break* (even if the class label has not flipped)? | recovered BOCPD candidate, unauthorized[1][8] | none | **NEW hypothesis** (change-point / run-length). Not a direction. Candidate for shadow, not a second governed classifier, unless the sitting says so. |
| S9 | What is volatility *doing next*, not only what it *did*? | `liquidity_stress_v1` is realized; GARCH/MS-GARCH recovered unauthorized[1][24] | none as forecast | **NEW hypothesis** (vol-state / forecast). Keep distinct from S4. |
| S10 | Which session / overlap / hour-of-week is this? | market-hours calendar; SQS baseline already session-windowed[1] | not a snapshot class | **Coordinate, not a label.** FX-specific. 24/7 crypto has no London/NY. Do not encode session as a regime class. |
| S11 | Do I trust this reading? | readiness markers; GitBook `regime_confidence`[1][6] | readiness already; confidence optional historically | **Readiness already in seam.** Classifier confidence is Epic 30 design (FreqAI-style trust/OOD/expiry is prior-research interpretation, not law).[9] |
| S12 | Is microstructure noise so high that any setup is fiction? | not in catalog; MQL5 "Noisy/Stressed" family[15] | none | **NEW hypothesis / feature**, likely inputs to S7 rather than a twelfth governed field. Futures DOM/VPIN does not transfer to spot without evidence. |

### Field split (summary)

**Already explicit on the ratified snapshot:** SQS score/hard-block, `feed_state`, `degraded_sensors`, labeler versions, readiness.[1][2]

**Cataloged V1 labelers Epic 26 must fold (not Epic 30):** identity, spread-state, gap-event, feed-state, SQS, degraded-sensors, fitted `liquidity_stress_v1`.[1][7]

**Other authorities, not MIS:** news windows, dead zone, handover, KSA levels, Book admission/sizing.

**Epic 30 design surface:** `regime_classifier_v1` class vocabulary, features, labels, windows, evaluation — plus whether S8/S9 are features of that classifier, sibling shadow labelers, or deferred.

**Later crypto sitting:** 24/7 absence of S6; SQS baseline without FX sessions; news source other than Forex Factory; no assumption of Asian/London/NY.

---

## 3. MQL5-derived idea families

### Corpus method (evidence)

Coverage file generated 2026-09-07: cataloged 3315, **ok 3057**, pending 0, failed 258.[11] Sections (ok): Examples 1215, Trading systems 692, Trading 516, Tester 237, Integration 125, Indicators 113, Statistics and analysis 71, Expert Advisors 56, Machine learning 21, Experts 8, Interviews 3.[11]

**Not done:** reading thousands of articles. **Done:** SQLite title+description keyword search (regime, scalp, session, volatility, HMM/GARCH/BOCPD, filter, news, spread, chop/ADX/Hurst/entropy) then **15 full reads** of high-signal hits. Vendor articles are method evidence, not a platform commitment. Local paths:

`C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/<id>.md`

### Full-read set (cap)

| id | Why selected | Path |
|---|---|---|
| 17737 | Statistical regime detector (trend/range/volatile) | `md/17737.md` |
| 17781 | Same series; EA playbook switching (**anti-pattern for QMX**) | `md/17781.md` |
| 20996 | Compression / transition / expansion vs trend-as-separate | `md/20996.md` |
| 22940 | Six-state priority-ordered environment reduction | `md/22940.md` |
| 23286 | Persistence entropy as regime indicator | `md/23286.md` |
| 23482 | BOCPD; risk meta-layer; honest non-edge | `md/23482.md` |
| 15033 | HMM integration; Viterbi/forward-backward on the page | `md/15033.md` |
| 16830 | HMM as **volatility filter** on a trend-follow backbone | `md/16830.md` |
| 17917 | HMM in ML trading systems (title/headings) | `md/17917.md` |
| 15223 | GARCH; forecast as the point of the model | `md/15223.md` |
| 23488 | catch22 features on volatility regimes | `md/23488.md` |
| 9804 | Bid/ask spread vs declared; news and off-hours cost | `md/9804.md` |
| 22516 | Session-aware time features; overlap vs non-overlap | `md/22516.md` |
| 21235 | News filter; Part 1 **entry-block only** | `md/21235.md` |
| 19944 | FX session boxes / handover of control | `md/19944.md` |

Indexed but not full-read (titles only, do not over-weight): 18821 hourly spreads, 3395 time filters, 4102 Asian night, 2930 Hurst, 15541 Nash+HMM, 23137 bagging regimes, 23444 Ehlers regime-switch EA, 22783 regime-adaptive mean-reversion.

---

### Top 5 idea families

These are **hypotheses for Book/KSA class-activation context**, not bot setups. None is an edge.

#### Family 1 — Priority-ordered environment reduction (stressed first, residual last)

**Evidence.** Microstructure Part 7 reduces eleven M1 measurements to six labels (Normal, Stressed, Noisy, Informed, Trending, Mean-Reverting), checks Stressed first, uses a **rule set rather than a trained model**, and is **not validated out-of-sample** in the article; the sample is **NQ M1 futures**, not FX or crypto spot.[15]

Composite directional score is a source claim. QMX must not put direction on a MIS snapshot that bots could eventually see.

**17737** uses a cheaper triad: autocorrelation (trend vs mean-reversion), volatility, trend strength → Trending / Ranging / Volatile.[12] **20996** splits **energy/constraint** (compression / transition / expansion) from **trend as an independent structural condition**.[14] That split is the cleanest vendor argument that "choppy" is not the opposite of "trend" on one axis.

**Interpretation for QMX.** This family matches the *scalper* job: collapse many noisy measures into one door-readable class with a reliability number, **fail closed on stress**. It is also the closest match to GitBook optional `trend|range|chaos` if chaos ≈ stressed/volatile/expansion. **Do not adopt NQ thresholds, VPIN, or the directional composite.** A rule-based stressed-first fold could theoretically live as a V1/Epic 26 **candidate in the shadow lane** without waiting for a trained `regime_classifier_v1`; that is a sitting question, not a recommendation to skip Epic 30's design story.

**QMX mapping:** S7 + S11 + S12. Consumers: Book door / KSA class block. Never bots.[2]

#### Family 2 — Online change-point as a "world just broke" meta-layer (BOCPD)

**Evidence.** BOCPD (Adams & MacKay) maintains a causal run-length posterior: probability the regime just ended, given data up to this bar and nothing after. The article states it is a **change-detection tool, not a direction-prediction tool**, and **not a source of edge**.[17]

Use 3 wraps it as a **risk meta-layer** around a *deliberately trivial* MA-cross, with a random-timed control of matched frequency so "trading less" is not mistaken for skill. All three modes still lose money. Limitations: sharp vol jumps collapse the posterior fast; quiet mean shifts may not fire; thin overlay sample; hazard/prior are inputs.[17]

This is the same recovered candidate QMX already named (unauthorized).[1][8] Prior research separately warns that offline `ruptures` is look-ahead and illegitimate as a live/backtest feature.[9]

**Interpretation for QMX.** Best MIS-shaped primitive in the vendor set: a per-instant **break probability + expected run length + not-ready during warm-up**, consumed as "do not evaluate new classes until the break cools," analogous to a door veto, **not** an entry. Keep it off the governed snapshot until ratification; shadow-lane is the existing seam.[2] Do not treat a change-point as a scalp trigger.

**QMX mapping:** S8. Possibly a feature of `regime_classifier_v1`, or a sibling candidate labeler. Asset-agnostic if the observation is log returns.

#### Family 3 — Hidden-state / Markov filter as volatility or persistence state (not a trade)

**Evidence.** 15033 presents HMM memory as hidden states and notes HMM as a **filter** on noisy series; it also walks forward, backward, Baum-Welch, and **Viterbi**.[18] 16830's explicit hypothesis: HMM clusters high/low vol; **enter the trend-follow only if next vol state is high, else stay out** — a filter, not a setup.[19] 17917 is the broader hmmlearn-in-trading article (headings only at this depth).[20]

**Interpretation / prior research, not vendor proof.** `hmmlearn.predict` / `predict_proba` are smoothing-contaminated; safe live use is filtered/forward only; regime as direction predictor in FX is historically weak; use as **risk filter**.[9] DEC-0262 already lists HMM as unauthorized recovered candidate.[1]

**Interpretation for QMX.** Eligible as the **model family sitting question** for `regime_classifier_v1`, or as a feature (filtered state probability of high-vol / trending). Hard rules for the sitting: no Viterbi traceback in live or in any label that will be replayed; persist frozen parameters; last-bar-only or an explicit one-step filter. Kronos remains a named recovered time-series candidate with **zero design** here — do not pretend it is specified.[1][8]

**QMX mapping:** S7 and/or S9. Epic 30 design story owns the family choice.[7]

#### Family 4 — Volatility-state: realized stress vs forecast vs feature panel

**Evidence.** SQS already prices **spread quality**, not volatility. `liquidity_stress_v1` is a **CPU quantile fit** (realized). MS-GARCH is a recovered QMX name with no implementation in QMX.[1]

15223's GARCH article states the forecast is a main objective of the analysis.[24] 23488 ports catch22 as a compact non-indicator description of *what a time series is doing* and tests it on volatility regimes; catch22 is not a collection of trading indicators.[25]

**Interpretation for QMX.** Three different numbers people collapse into "vol":

1. Realized stress vs own history → already `liquidity_stress_v1` (Epic 26).
2. Conditional forecast σ²_{t+h} → GARCH/MS-GARCH family (Epic 30 candidate, unauthorized today).
3. High-dimensional "what is this window like?" → catch22 / entropy / Hurst as **features**, not snapshot classes.[16][25][30]

A scalper needs (1) before looking, and sometimes (2) to refuse violent classes. (3) belongs in the training design, not as twenty-two governed fields.

**QMX mapping:** S4 already; S9 new; S12 features. Do not replace SQS with ATR.

#### Family 5 — Session and news as coordinates and other-authority windows (not regime classes)

**Evidence.** 19944: each FX region has different speed/vol/liquidity; session identity is the adaptation cue.[26] 22516: hour-of-day is cyclical; London–NY overlap 13:00–16:00 UTC is the most active FX window; pooling overlap with non-overlap is a distributional error.[22]

4102 (indexed): Asian "night" is often flat on EURUSD-class majors and active on JPY crosses — pair×session, not a global dead flag.[29] 3395: time filters exist to avoid flat or high-vol periods.[28]

9804: live spread vs declared; news and off-hours inflate true cost — scalper context QMX already models as SQS, not as a clock heuristic.[21] 18821 treats FX as a time-driven liquidity cycle across financial centers, the same cost/session coordinate rather than a regime class.[27] 21235 Part 1 **limits itself to entry blocking** to avoid side effects, aligned with QMX L39.[23]

**Interpretation for QMX.** Operator's four-way `choppy vs trend vs news vs dead` **mixes two ontologies**. Chop/trend (and violent/quiet) are **statistical**. News/dead are **calendar windows QMX already owns** (CT-31, KSA). Putting news/dead inside `regime_classifier_v1` would duplicate AD-38, fight 24/7 crypto, and make the classifier need a news feed. **Do not.** Emit session-phase as an optional **coordinate** if the sitting wants it on the snapshot; keep windows as windows.

SQS baseline is already "named session window" — the FX-shaped part of cost sensing.[1] A 24/7 crypto sitting must re-specify that conditioning (clock-hour, weekday, or none), not copy London.

**QMX mapping:** S5, S6, S10. Asset-agnostic seam stays; session features are FX-specific.

---

### Anti-patterns (vendor source vs QMX governance)

- **EA switches playbooks from the detector** (17781: trend-follow / mean-reversion / breakout + lot/SL/TP by regime).[13] In QMX that is Book/KSA class activation after examination, never MIS→bot.
- **Change-point or HMM as entry** — contradicted by the better vendor articles themselves.[17][19]
- **Offline segmentation labels in a backtest** — look-ahead.[9][17]
- **Futures microstructure (VPIN, Roll, NQ M1) as spot-crypto or spot-FX truth** — transfer assumption, no evidence in this read.[15]
- **Comfortable Scalping (1509, sampled then dropped):** execution-UI for discretionary scalping; no regime content.

---

## 4. What belongs in Epic 30 vs a later crypto sitting

### Epic 26 (not this brief, but the seam that must exist first)

Rule-based six + fitted `liquidity_stress_v1` + shadow-lane seam. Does **not** train `regime_classifier_v1`.[7] Scalper needs S1–S4 and readiness land here if they land at all in V1.

### Epic 30 (GAP-0051) — last node epic

Story 30.1 is already the right container: **design before model**. It must rule family, features, as-of law, label method, **closed class vocabulary**, all-session windows, leakage, splits, evaluation, refusal criteria.[7] Recovered Kronos/HMM/BOCPD/MS-GARCH get no authority by being evaluated.[1][7]

**Belongs in Epic 30 (this sitting's job when it happens):**

- Class vocabulary for `regime_classifier_v1` that a Book can map onto **strategy-class activation/block** (chop vs trend vs violent/quiet — **not** news vs dead).
- Causal inference law (filtered/forward only; no smoothing; frontier-as-of).
- Whether BOCPD run-length is a **feature**, a **sibling candidate labeler**, or out.
- Whether GARCH forecast is in or out vs relying on `liquidity_stress_v1`.
- Label generation that does not peek (no future-bar regime painted backward).
- Freeze-and-register artifact; operator-machine hours-long script; shadow then one full affected-Book recertification.[3][7]
- Evaluation as **door usefulness** (does class X predict that strategy-class Y should have been blocked?), not as PnL of a vendor EA.

**Does not belong in Epic 30:**

- Book sizing, leash, R, viability.
- Piping labels to bots.
- Replacing SQS, news windows, or KSA.
- Claiming Kronos is the model.
- Crypto venue plumbing, funding, multi-exchange basis.[10]
- Populating STRATS.

### Later crypto sitting (after / beside first live market)

Crypto is a **plumbing** problem more than a new trading skill.[10] For MIS specifically:

| Topic | FX (current calendars / SQS) | 24/7 crypto spot |
|---|---|---|
| Dead zone / handover | CT-31 exists[1] | **Absent** — do not invent crypto "sessions" as FX clones[1] |
| SQS baseline window | market-hours session id[1] | Needs a sitting: clock-hour, weekday, rolling, or venue-hours |
| News | Forex Factory weekly file, pair-scoped | Different source; token listings / exchange incidents ≠ NFP |
| Session features (Family 5) | London/NY overlap is load-bearing in vendor FX ML[22] | Do not ship |
| Microstructure features | Even FX spot ≠ NQ futures DOM[15] | Exchange volume / funding / perp basis are **not** spot-crypto truth without evidence[10] |
| Seam (snapshot, closed consumers, shadow, readiness) | Asset-agnostic already[2] | **Keep** |

First live market may be crypto spot. That is an argument to **keep Epic 30's classifier asset-agnostic** (returns, realized vol, change-point on log returns) and to **defer FX-session coordinates** rather than bake Tokyo/London/NY into `regime_classifier_v1`.

---

## 5. Recommended next BMAD / factory move

**Do not implement. Do not open a documentation-factory mutation. Do not populate STRATS. Do not run `bmad-architecture` in this increment.**

QMX pipeline (project rule): brainstorming as needed → PRD/architecture as needed → documentation-factory → epics-and-stories → factory lanes. Architecture may run before PRD when `docs/` is the requirements body. Never `bmad-sprint-planning` or `bmad-build`.

**Recommended next sitting (handoff into `bmad-architecture` later, coaching path default):**

1. **Treat this file as the input package** for Epic 30 Story 30.1, not as a spine.
2. When the operator wants the sitting, run **`bmad-architecture` at epic altitude for Epic 30 only**, coaching path, inheriting as **read-only constraints**:
   - DEC-0204 closed consumers / seam / shadow / no trained model in V1
   - DEC-0153 SQS block-only, snapshot-only delivery
   - DEC-0262 catalog + unauthorized recovered families
   - AD-38 / CT-31 windows own news/dead/handover
   - L39 entries-only blocks
   - GAP-0051 training law (offline, seed/window/`fp1`, registry artifact, recertify)
3. **First decision to elicit (not infer):** class vocabulary. Operator said choppy / trend / news / dead. This brief's interpretation: **news and dead stay windows**; classifier vocabulary is behavior (at minimum chop vs trend vs stressed/violent, residual/unknown). That is a load-bearing fork — show alternatives, do not silently draft.
4. **Second decision:** is `regime_classifier_v1` a trained model (catalog), a rule-based stressed-first fold (Family 1, could shadow in Epic 26), or both (rules now, trained later)? Catalog currently says **trained**, undesigned.[1]
5. Factory: **Epic 26 seam still precedes any governed consumption.** Epic 30.1–30.6 may run on a disjoint branch as research; 30.7–30.8 wait for a stable shadow seam.[7]
6. **Crypto sitting stays later.** Do not expand GAP-0051 into venue/crypto plumbing.

Optional cheap precursor: a short `bmad-brainstorming` only on class vocabulary, then the architecture increment. Skip a new PRD — FR-079 / Epic 30 already exist.

---

## 6. Open questions for the sitting (not answers)

1. Closed class set: GitBook `trend|range|chaos` vs operator `choppy|trend|news|dead` vs Family 1 six-state vs 20996 compression×trend grid?
2. Does "dead" mean CT-31 dead zone, statistical quiet, or SQS-untradable? (Three different doors.)
3. Rule-based regime prior in V1 shadow, or wait for the trained artifact?
4. BOCPD: feature vs sibling labeler vs out?
5. HMM vs jump model vs LightGBM-on-features vs Kronos — all unauthorized until chosen; look-ahead law is not optional.[9]
6. Label generation: future-horizon outcome (leaky), concurrent vol/trend statistics (causal but circular), or human/rule teacher?
7. First training corpus: FX sessions (Story 30.1 says all three sessions) vs crypto 24/7 first live market — conflict to surface, not to paper over.[7]
8. What does Book *do* with a class? (Activation/block of strategy classes only — sizing out of scope here, but the sitting must name the **consumer effect** without inventing R.)

---

## Scalper-need list (extract)

S1 feed honesty — already in seam.
S2 cost/spread — SQS in seam; `spread_state` cataloged for Epic 26.
S3 gap/jump — cataloged Epic 26.
S4 realized liquidity stress — cataloged fitted Epic 26.
S5 news window — CT-31/KSA, not MIS.
S6 dead/handover — CT-31, FX-only, absent 24/7.
S7 behavior class (chop/trend/violent) — Epic 30 `regime_classifier_v1`.
S8 just-broke — BOCPD hypothesis, unauthorized.
S9 vol forecast — GARCH/MS-GARCH hypothesis, unauthorized; not S4.
S10 session coordinate — FX-specific, not a class.
S11 trust/readiness — readiness in seam; classifier confidence Epic 30.
S12 microstructure noise — feature input, not a twelfth governed field; no silent futures→spot transfer.

## Top 5 idea families (extract)

1. **Stressed-first environment reduction** — `md/22940.md`, `md/17737.md`, `md/20996.md`
2. **Causal change-point meta-layer (BOCPD)** — `md/23482.md`; QMX recovered name only
3. **HMM / Markov filter as vol or persistence state** — `md/15033.md`, `md/16830.md`, `md/17917.md`; look-ahead trap in `workroom/research/08-mis-ml-regime-models.md`
4. **Volatility-state split (realized vs forecast vs feature panel)** — catalog `liquidity_stress_v1`; `md/15223.md`; `md/23488.md`
5. **Session/news as coordinates and other-authority windows** — `md/19944.md`, `md/22516.md`, `md/21235.md`, `md/9804.md`, `md/3395.md`, `md/4102.md`

---

## Sources

[1] file:///C:/Users/Mubarak/Desktop/QMX/docs/glossary.md — QMX glossary MIS/SQS/snapshot/windows
[2] file:///C:/Users/Mubarak/Desktop/QMX/docs/components/trading-node.md — QMX trading-node TN-19 MIS seam
[3] file:///C:/Users/Mubarak/Desktop/QMX/docs/decisions/ADR-0019-trading-node.md — ADR-0019 trading node
[4] file:///C:/Users/Mubarak/Desktop/QMX/docs/gap-report.md — QMX gap-report GAP-0051
[5] file:///C:/Users/Mubarak/Desktop/QMX/docs/decisions/ADR-0011-deferred-consumer-products.md — ADR-0011 deferred consumer products
[6] file:///C:/Users/Mubarak/Desktop/QMX/archive/recovery/trading-node-delta/work/gitbook-baseline.md — GitBook baseline CT-MIS-01
[7] file:///C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/epics.md — QMX epics Epic 26/30
[8] file:///C:/Users/Mubarak/Desktop/QMX/tracker/map.md — QMX tracker map Kronos/BOCPD
[9] file:///C:/Users/Mubarak/Desktop/QMX/workroom/research/08-mis-ml-regime-models.md — Prior art MIS ML regime models
[10] file:///C:/Users/Mubarak/Desktop/QMX/workroom/research/07-crypto-inefficiencies.md — Crypto inefficiencies scan
[11] file:///C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/coverage.md — MQL5 library coverage
[12] https://www.mql5.com/en/articles/17737 — MQL5 17737 regime detector P1
[13] https://www.mql5.com/en/articles/17781 — MQL5 17781 regime detector P2
[14] https://www.mql5.com/en/articles/20996 — MQL5 20996 market state classification
[15] https://www.mql5.com/en/articles/22940 — MQL5 22940 microstructure regime classification
[16] https://www.mql5.com/en/articles/23286 — MQL5 23286 persistence entropy
[17] https://www.mql5.com/en/articles/23482 — MQL5 23482 BOCPD
[18] https://www.mql5.com/en/articles/15033 — MQL5 15033 HMM integration
[19] https://www.mql5.com/en/articles/16830 — MQL5 16830 HMM volatility filter
[20] https://www.mql5.com/en/articles/17917 — MQL5 17917 HMM ML trading
[21] https://www.mql5.com/en/articles/9804 — MQL5 9804 bid/ask spread analysis
[22] https://www.mql5.com/en/articles/22516 — MQL5 22516 session-aware time features
[23] https://www.mql5.com/en/articles/21235 — MQL5 21235 news filtering P1
[24] https://www.mql5.com/en/articles/15223 — MQL5 15223 GARCH
[25] https://www.mql5.com/en/articles/23488 — MQL5 23488 catch22 volatility regimes
[26] https://www.mql5.com/en/articles/19944 — MQL5 19944 forex sessions
[27] https://www.mql5.com/en/articles/18821 — MQL5 18821 hourly movement and spreads
[28] https://www.mql5.com/en/articles/3395 — MQL5 3395 time filters
[29] https://www.mql5.com/en/articles/4102 — MQL5 4102 Asian night trading
[30] https://www.mql5.com/en/articles/2930 — MQL5 2930 Hurst exponent
