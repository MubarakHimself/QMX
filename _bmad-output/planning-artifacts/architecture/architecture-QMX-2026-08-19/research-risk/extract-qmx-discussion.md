# QMX Risk-Sitting Evidence Dossier — QMX-discussion corpus (oldest layer)

**Extractor scope:** `C:/Users/Mubarak/Documents/Claude/QMX-discussion/` (READ-ONLY evidence).
**Task:** Book/BMS/risk design, GAP-0039..0046. Record every finding with its corpus layer + date. I record precedence, I never decide it.

---

## Layer map INSIDE this corpus (critical — read first)

This corpus is not one generation. It contains three distinct internal sub-layers, and the checklist's "Book/BMS/seven-doors/money-ladder" vocabulary lives ONLY in the two newer sub-layers, as second-hand captures of a GitBook that is a *different* corpus:

- **LAYER A — Oldest bot-centric vault (~2026-04-25 → 2026-05-17).** Dirs `01-System-Overview/`, `02-Components/*`, `04-Integration-Flows/`, `05-Deployment/`, and `bmad-docs/planning-artifacts/*`. Vocabulary: **bot / slot / half-Kelly / DPR tiers / equity bands / kill-switch GREEN..BLACK / asymmetric SL-TP**. **There is NO "Book" and NO "BMS" here.** This layer is the *original intent* behind exits, kill switch, news windows, SQS. Component specs self-label "Canonical v1.0/v2.0" — but the newer layers explicitly strip that authority (see below).
- **LAYER B — Discussion-layer distillation of the newer GitBook "new-core" (GitBook ruling pass dated 2026-07-08; ingested/distilled 2026-07-17).** Files `.brain/entities/qmx-new-core.md`, `.brain/sources/qmx-gitbook-newer-docs.md`, `.brain/decisions/decision-ledger.md`. Vocabulary: **books, BMS desks, seven doors, money ladder (FORM-0001..0010), 17 laws, treasury cycles, Examination Engine, CT-BOOK/CT-BMS contracts, KSA GREEN..BLACK**. This is where CT-BOOK/CT-BMS/FORM/seven-doors first appear in MY corpus — but only as a *summary* of the GitBook, not a field-level schema.
- **LAYER C — Discussion-layer clash reports + old-vault extractions (2026-07-17/18).** Dir `outputs/*`. These reconcile Layer A (old vault) against Layer B (new core), tagging each old mechanic `[UNRATIFIED]` / `[RE-ANCHOR]` / `[BINDING]`. They carry the fullest *verbatim* record of both the old exit/CB/SQS mechanics AND the new-core seven-doors/money-ladder, with explicit clash flags.

**Recorded precedence statements the corpus makes about itself** (I record, I do not adjudicate):
- `.brain/decisions/decision-ledger.md:81` — "**GitBook is the sole documentary authority.** … all pages distilled from the old local documentation were removed from this brain."
- `outputs/qml-spec.md:8` — "Rule of precedence: **the new version stands above.**"
- `outputs/sltp-authority-spec.md:16` — "Where they disagree, **the book rules win.**"
- `outputs/*` headers repeatedly: old-vault "Canonical v1.0" label "**carries no authority now**" (e.g. `sltp-authority-spec.md:2`, `backtest-engine-spec.md:3`, `bot-registry-lineage-spec.md:3`, `dpr-prs-spec.md:3`).

Every finding below is tagged **[A]/[B]/[C]** for its sub-layer.

---

## Topic 1 — Book schema (fields, versioned book-type schema, seven doors)

**No field-level Book schema (CT-BOOK-01/02 contents) exists anywhere in this corpus.** Only a prose summary of the GitBook Book construct exists (Layer B), plus the seven-doors list (Layers B/C).

**[B] Book = pod definition** — `.brain/entities/qmx-new-core.md:28-33`:
> "**Book** — a pod with charter, capital, roster, profile, rules, journals. Charter fills four slots: game played, money shape, customer + headline metric, death condition (DEC-0027). Template ("sealed Sections 0–5", ADR-0002) vs instance values strictly split. First instance: **Scalper Book** (COMP-BOOK-SCALPER) — "treasury-customered cash-flow machine judged by swept cash per month per dollar of seed"; may never compound between cycles."

**[B] Template/instance split** — `.brain/decisions/decision-ledger.md:102-104`:
> "**ADR-0002 Template/instance split:** book template = sealed Sections 0–5, documented once; instances own their values (uniform values dead, DEC-0024)."

**[B] Contracts named (no bodies)** — `.brain/entities/qmx-new-core.md:80-83`:
> "17 YAML contracts (CT-BOOK-01/02, CT-EXAM-01/02, CT-MIS-01/02, CT-BMS-01..05, CT-KSA-01, CT-ADAPTER-01, CT-PAPER-01, CT-NOTIFY-01, CT-DATA-01, CT-QML-01). Rule: "if a field is not in the contract, it does not cross the boundary." `registry/variables.yaml` (~25 typed entries) + `registry/formulas.yaml` (FORM-0001..0010)."

**[C] Seven doors — VERBATIM, ratified order (DEC-0035)** — `outputs/clash-report-sltp-vs-book.md:14-18` and `outputs/sltp-authority-spec.md`:
> "seven doors in ratified order (footprint → viability veto → R_max → daily budget → breaker → exposure ledger → KSA → adapter, DEC-0035)"

**[B] Seven doors (alt phrasing)** — `.brain/entities/qmx-new-core.md:35-37`:
> "**Seven doors** (per trade intent, before adapter): footprint, viability veto, R_max, daily budget, breaker, exposure ledger, kill switch. Every refusal signs the **veto ledger** (L11)."

**[C] Old→new door mapping** — `outputs/qml-spec.md:159`: "Nine safety hooks + Intent Aggregator | Seven doors (footprint, viability veto, R_max, daily budget, breaker, exposure ledger, kill switch); every refusal signs the veto ledger (L11) | Map hooks→doors; veto-ledger emission". The old Layer-A analogue is the **nine safety hooks** (`outputs/qml-spec.md:122`): "session, session_warmup, kill_switch, news, dpr(two-strike), spread(sqs_hard_block), regime(HIGH_CHAOS), feature_quality, concurrent_slot."

**Layer-A nearest analogue to a "book":** there is none. Layer A's identity unit is the **BotSpec** (Topic 4). The word "book" in Layer A means the account/ledger generically (e.g. `02-Components/01-risk-and-sizing/00-overview.md:11` "without exposing the book to ruin").

---

## Topic 2 — BMS schema (CT-BMS-*, what BMS owns vs Book)

**No field-level BMS schema exists.** Only the four-desk prose summary (Layer B).

**[B] BMS four desks** — `.brain/entities/qmx-new-core.md:50-53`:
> "**BMS** — four desks: Treasury, Exposure, Records, Reporting (DEC-0045). Records owns the ONLY journal write path, append-only (DEC-0046); Reporting has zero authority. Unexplained BMS/broker drift = technical kill (L14)."

**[B] Authority boundary (BMS vs Book vs bot)** — `.brain/entities/qmx-new-core.md:22-24`:
> "**Bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market.** Hierarchy: bot → book → BMS → operator."

**[C] BMS never reaches into a book** — `outputs/clash-report-sltp-vs-book.md:24`: "**BMS**: never trades, sizes, or reaches inside a book (DEC-0045)."

**[B] KSA policy owned by BMS, enforced by adapter** — `.brain/entities/qmx-new-core.md:54-56`: "**KSA** … BMS owns policy; adapter enforces."

Open BMS gaps recorded: GAP-0008 (Exposure Desk v2 / cross-book cap), GAP-0010 (BMS §1–2 assignments) — `.brain/sources/qmx-gitbook-newer-docs.md:46-50`.

---

## Topic 3 — Cardinalities (Book↔BMS, bot↔Book, Book↔account/venue)

**[B] bot↔Book: a book runs ≤3 concurrent live bots.** `.brain/entities/qmx-new-core.md:66-67`: "Risk seats: `max_concurrent_live_bots = 3` (ENH-0007)." Same value `outputs/qml-spec.md:151`. A book's `roster` is its bot set (`qmx-new-core.md:28`).
**[C] Book↔account: replay is per-book-instance** — `outputs/clash-report-backtest-replay.md:48-50`: "a backtest is against a BOOK, not just a bot … the new one must load a book profile." Confirms a Book carries its own capital/profile/values (instance-owned).
**[B] Hierarchy is bot → book → BMS → operator** (`qmx-new-core.md:22-24`). This implies BMS sits ABOVE books, and GAP-0008 "cross-book cap" (Exposure Desk) implies **one BMS spans multiple books** — but the exact Book↔BMS multiplicity is **not numerically ratified** in this corpus.
**Book↔account/venue multiplicity (may one Book bind accounts at several venues?): NOT FOUND.** COMP-ADAPTER is "platform-blind" (`qmx-new-core.md:74`); no statement binds one book to multiple venues/accounts. Layer A binds a *bot* to exactly one `account_id`/`account_mode` at a time (`02-Components/07-bot-registry-and-lifecycle.md:64-65`), flipped live↔demo by the demotion service (Topic 7).

---

## Topic 4 — Book/BMS lifecycle states & modes; seat-state vs book-mode split

**No "Book mode" or "seat-state" enum exists in this corpus.** The only lifecycle state machine is Layer-A's **bot lifecycle** (bot-centric), which the newer layers say must be re-derived onto treasury cycles + leash rungs.

**[A] Bot lifecycle states (RegistryRecord)** — `01-System-Overview/02-data-contracts-overview.md:45`:
> "`lifecycle_state` | enum | `candidate` | `paper-trading` | `live` | `demoted` | `retired`"

**[A] Expanded lifecycle set (2026-05-01)** — `02-Components/07-bot-registry-and-lifecycle.md:103-123`:
> States: `POST_WF1` (pseudo-state, NOT a registry row), `POST_WF2` (first registry state), `PAPER_TRADING`, `LIVE` (with `phase` ∈ `probation`|`full`|`null`), `DEMOTED`, `PAUSED`, `RETIRED` (terminal). Allowed-transition matrix at `:127-141`; forbidden: RETIRED→anything (`:145`).

**[A] account_mode split** — `02-Components/07-bot-registry-and-lifecycle.md:65`: "`account_mode` | Enum | `LIVE` or `DEMO`. Source of truth for routing decision in the broker adapter." (This is the closest Layer-A analogue to a "book-mode".)

**[C] The state machine must be rebuilt onto the new core** — `outputs/bot-registry-lineage-spec.md:73-76`:
> "[RE-ANCHOR: the whole machine maps onto Treasury cycles + Exam certification + leash rungs — e.g. demotion→bench-to-paper, retirement→ death condition/sunset review; the state SET must be re-derived, but the matrix discipline (explicit triggers, no direct field writes) is the keeper.]"

**[B] Leash chain (the new-core replacement for CB-driven state changes)** — `.brain/entities/qmx-new-core.md:38-40`:
> "**Leash chain** (DEC-0037): ambient governor → day closure → bench-to-paper → chorus flag → kill-line stand-down → classed kill switch → hold-time force-flat."

**[B] KSA five levels + escalate-only** — `.brain/entities/qmx-new-core.md:54-56`:
> "**KSA** — five levels GREEN/YELLOW/ORANGE/RED/BLACK (DEC-0043); trigger classes scheduled_news/black_swan/connectivity/unknown_state; escalate-only automation, de-escalation is A1 (L8). BMS owns policy; adapter enforces."

---

## Topic 5 — Book versioning + compatibility (scalping-book-v2 = NEW Book)

**No "book versioning" rule exists in this corpus.** The nearest is (a) Layer-A's **BotSpec immutability / new-id-on-mutation** rule, and (b) Layer-B's template/instance split with the treasury "no compounding between cycles" rule. The specific "scalping-book-v2 = NEW Book, never inherits v1 ledger" claim is **NOT FOUND** verbatim; the closest supporting primitives:

**[A] BotSpec immutable; mutation = new id + parent_id** — `02-Components/07-bot-registry-and-lifecycle.md:22`:
> "It is immutable after creation — mutation produces a new BotSpec with a new id and a `parent_id` pointing to its progenitor."
Mutation types `FEATURE` (same archetype) vs `ECOLOGICAL` (archetype change) — `:155-158`. Orphan rejection: parent must exist — `:295`.

**[B] Books may never compound between cycles; money ratchets, knowledge persists** — `.brain/entities/qmx-new-core.md:46-49`:
> "**Treasury** — virtual capital ledger; **cycle** = seed→cap; sweep at rollover only; equity resets to seed; money ratchets between cycles; knowledge persists (L5). Seed S=$500, kill-line K=$200, cap C=2.5×S (registry)."

**[C] Backtest is against a book instance profile** — `outputs/clash-report-backtest-replay.md:48-51` (see Topic 3) — implies each book instance carries its own registry values, the mechanism a "v2 book" would use for a fresh ledger. But the explicit "new version = new book, no ledger inheritance" ruling is not written here.

---

## Topic 6 — Exit ownership (bots vs Book; forced exits; fast invalidation; dynamic SL/TP; position-safety authority)

This is the richest clash in the corpus. **Layer A gives a full, verbatim SL/TP authority. Layer C flags that the new-core Book system has NO stop-management component and that exit ownership is an open ruling.**

**[A] Bots do NOT own stops — system-owned SL/TP Authority** — `02-Components/03-execution-safety-and-asymmetric-sl-tp.md:11`:
> "Individual strategy instances do not own, compute, or amend their own stops; they publish a trade intent that includes the original stop and target distances, then relinquish control. The Authority holds the mandate from that point forward."

**[A] Asymmetric policy VERBATIM** — same file `:16-34`:
> "**Take-profit: continuous trailing.** … There is no hard cap on how far TP can extend; the extension is bounded by the continuation signal weakening.
> **Stop-loss: one-shot move to breakeven.** When a position reaches +1R of unrealised profit (equal to the original risk distance), the stop-loss is moved once to the breakeven price (entry ± spread). After that move, the SL does not trail further."
> P&L ladder (`:28-34`): "Entry → SL at original stop, TP at original target / P&L reaches +1R → SL one-shot move to breakeven / P&L continues + → TP extends per continuation model / Reversal to BE → Stopped at breakeven (0R loss unit) / Reversal to SL → Stopped at original stop (1R loss unit)."

**[A] Who moves stops, when** — one-shot BE at +1R, `sl_at_breakeven` flag set once, "never reset for the lifetime of the position" except a kill-switch override (`03-...sl-tp.md:104-115`). TP extension rule `f(continuation_prob, unrealised_pnl_pips)`, monotonically increasing, computed in the shared contract layer not the Authority (`:79-95`). On MI timeout: "hold last-set TP; do not extend; do not close" (`:241-251`).

**[A] Amendment idempotency & priority** — `AmendInstruction.priority`: kill-switch = 0 (highest), normal = 10 (`03-...sl-tp.md:60-71`); emit only if move exceeds `AMENDMENT_THRESHOLD_PIPS` (`:256-264`).

**[C] The new Book core has NO stop component — verdict** — `outputs/clash-report-sltp-vs-book.md:7-10`:
> "**the new system has NO stop-management component — and that absence is not neutral. The book's money math silently assumes answers about stop behavior in at least three load-bearing places.**"
And `:30-32`: "**Nowhere**: who sets the stop, who may move it, whether TP trails, whether breakeven moves exist … The words "stop-loss" and "take-profit" do not appear as owned behavior in any component page."

**[C] Proposed resolution — stop policy = book MONEY SHAPE; a single Position Safety service** — `outputs/clash-report-sltp-vs-book.md:68-83`:
> "**Stop policy is part of a book's MONEY SHAPE.** … A single **Position Safety service** executes whatever policy the book declares (one implementation, per-book configuration — exactly the template/instance split, ADR-0002). It declares itself under ADR-0001 as: senses (MI continuation input, information-only per L6), **decides post-entry stop amendments**, executes via adapter; accounts nothing (journals via BMS Records; every amendment appended — veto-ledger culture, L11, matching the old AmendEvent log)."

**[B] Forced-exit / fast-invalidation organs in the new core** — the leash chain includes **hold-time force-flat** (a position-closing authority) and classed kill switch (`qmx-new-core.md:38-40`; `clash-report-sltp-vs-book.md:24-27`). New-core kill levels RED/BLACK force BE / force-close (Topic 10).

**[A] Layer-A forced exits (for reference / donor):** kill-switch RED → SL to breakeven; BLACK → all closed at next fill (`02-Components/09-kill-switch-authority.md:31-32`). Connectivity kill switch: always-armed broker-side hard SL as orphan-safety floor (`09-kill-switch-authority.md:354-374`).

---

## Topic 7 — Paper mode (bench-to-paper, paired demo bindings, duplicate-order prevention, live↔paper, evidence comparability)

**[A] Paper = real execution on a real demo account, same adapter code (NOT a simulator)** — `02-Components/08-paper-trading-demotion-service.md:14`:
> "Paper trading in this architecture means live execution against a real demo account at the same broker, through the same broker adapter code, under demo credentials."

**[A] One adapter, two credential profiles (paired demo binding)** — `08-...demotion-service.md:26-33`:
> "`EXECUTION_LIVE` | Live account | All bots in `LIVE` … `EXECUTION_DEMO` | Demo account | All bots in `PAPER_TRADING` and `DEMOTED`." Demotion is "a routing flip, not a re-implementation. The code path from bot signal generation to order submission is identical in both modes." (Evidence-comparability rationale: `:33`.)

**[A] Duplicate/split-brain prevention** — `08-...demotion-service.md:134-135`:
> "If the registry mutation (step 1) fails, the routing table is not updated … The bot is suspended pending operator intervention. This prevents a split-brain state where the registry says `DEMO` but the adapter is still routing to `LIVE`."
Atomic three-step demotion sequence (`:102-108`); demo-unavailable → suspend, never continue live (`:121-131`).

**[A] live↔paper transitions** — CB 2nd hit → DEMOTED→demo; daily rollover reinstates to **PAPER_TRADING** (not LIVE); re-promotion requires rolling tier ≥T2 + ≥10 positive demo trades + **manual approval gate** (`08-...demotion-service.md:62-73`). Paper window configurable per archetype (7/14/21 days) (`:231-249`).

**[B/C] New-core reframing: paper is a FROZEN COUNTERFACTUAL DIAGNOSTIC, not a comeback arena** — `.brain/entities/qmx-new-core.md:73` ("COMP-PAPER (frozen counterfactual diagnostic, L13)"); `outputs/clash-report-bot-rating.md:44-47`:
> "New: paper mode is a **frozen counterfactual diagnostic** (L13), and kill-line means paper until re-seed at the cycle boundary (DEC-0023). Paper is a morgue window, not a comeback arena."
**[B] Law L9: news blocks live AND paper identically** — `qmx-new-core.md:92-93`.
**[C] The old redemption/rehab loop is structurally dead** — `outputs/clash-report-alpha-decay.md:42-50`, `clash-report-bot-rating.md:44-47`.

---

## Topic 8 — News protection (windows, severity tiers, currency→instrument, open-position behavior, overrides)

**[A] Severity tiers + before/after windows (minutes) — VERBATIM** — `02-Components/09-kill-switch-authority.md:85-90`:
> "| Impact Rating | Pre-Release Action | Post-Release Window |
> | LOW | No level change | No level change |
> | MEDIUM | YELLOW at T-5 minutes | GREEN at T+10 minutes |
> | HIGH | ORANGE at T-15 minutes | GREEN at T+20 minutes |
> | EXTREME | RED at T-30 minutes | YELLOW for 60 minutes, then GREEN |"

**[A] Soft-kill staggered exit schedule (scheduled news)** — `09-kill-switch-authority.md:328-336`:
> "**T-15 min**: block all new entries on affected symbols … **T-13, T-11, T-9, T-7, T-5 min**: staggered exit in 25% chunks every 2 minutes … **T-5 min target**: 0% exposure … **T+15 min**: slow scan resume … bot weights remain at `× 0.1` until volatility has demonstrably normalised." Default settling time 15 min (`:336`).

**[A] Currency→instrument mapping owned by MIS (News Scope Resolver)** — `02-Components/04-market-intelligence-service.md:322`:
> "The News Scope Resolver maintains a currency-impact map: a news event tagged as affecting USD blocks all USD-denominated pairs." Symbol-scoping lives inside MIS, not in KSA/bots (`04-market-intelligence-service.md:310`, `09-kill-switch-authority.md:92`).

**[A] Geographic auto-rotation (region_shift)** — `09-kill-switch-authority.md:378-425`: HIGH/EXTREME news currency→region (Asia/Tokyo, Europe/London, US/NY) auto-shifts the active pair set to non-news regions; default "auto-rotate, log, no prompt"; operator can override.

**[A] Open-position behavior + news_state snapshot fields** — MIS snapshot carries `news_kill_active`, `news_kill_level` ∈ `{NONE, TIGHTEN, HALT_ENTRIES, FLATTEN}`, `news_kill_symbols`, `news_kill_expires_utc` (`04-market-intelligence-service.md:266-269`). Note this news-level enum (`04-...`) DIFFERS from the KSA five-level enum — see Contradictions.

**[B] New-core: L9 news blocks live AND paper identically** (`qmx-new-core.md:92-93`). **[C] region-shift rotation is DEAD in the new core (DEC-0021)** — `outputs/qml-spec.md:156`, `clash-report-alpha-decay.md:38-40`. So Layer-A geographic shifting was later killed.

---

## Topic 9 — SQS / spread-quality (formula, inputs, thresholds, cadence, hysteresis, WHY)

All Layer A. This is the original SQS design.

**[A] Formula — VERBATIM** — `02-Components/05-spread-quality-service.md:42-43`:
> "`sqs_score = historical_avg_spread(symbol, session_window) / current_live_spread(symbol)`"
> "A score of **1.0** means the current spread exactly matches the historical average. A score **above 1.0** means … tighter than average … A score **below 1.0** means … wider than average."

**[A] Session-conditioned denominator** — `05-...:48-52`: historical avg is per-canonical-session-window, not a flat 24h average.

**[A] Hard-block thresholds per instrument category** — `05-...:77-83`:
> "Major FX 0.60 · Minor FX 0.55 · FX exotic 0.45 · Index CFDs 0.65 · Commodity CFDs 0.50." Per-symbol/per-session overridable via config (`:85`).

**[A] Hysteresis** — `05-...:88-89`:
> "once `hard_block=True` is set, the score must exceed `hard_block_threshold + hysteresis_band` (default: 0.05) before `hard_block` reverts to `False`."

**[A] Outlier guard** — `05-...:133-137`: if `current_live_spread > historical_avg_spread + 4*historical_std_spread` → `hard_block=True`, `sqs_score` clamped to 0.0, `quality_tag=DEGRADED`.

**[A] Soft sizing multipliers** — `05-...:99-105`: ≥0.90→1.00; 0.75–0.90→0.85; 0.65–0.75→0.70; threshold–0.65→0.50; <threshold→hard block.

**[A] Cadence & latency** — per quote update during active session; per-quote compute ≤3ms; baseline daily recompute 30 min before Tokyo open, weekly full re-fit Sunday 22:00 UTC (`05-...:122-129`, `:222-224`).

**[A] WHY it existed** — `05-...:15`: "it carries symbol-aware baseline data … its hard-block signal is one of the few inputs capable of informing an unconditional no-entry decision regardless of regime state or position-sizing output." Conservative-by-default: every ambiguous/failed state → `hard_block=True` (`:216`). Weekend/illiquid guard: score undefined, sentinel `-1.0`, implicit HALT_ENTRIES (`:54-56`).

**[A] Authority boundary:** SQS computes; MIS transports `sqs_hard_block`; **Risk Authority decides the block** (`05-...:17`, `:73`). **[C] new-core:** `sqs_hard_block` becomes the "footprint / viability veto" door input; SQS still information-only.

---

## Topic 10 — Kill switch / KSA (authority, scopes, escalate-only, effect vocabulary, adapter)

**[A] Five-level state machine + effects — VERBATIM** — `02-Components/09-kill-switch-authority.md:26-32`:
> "| GREEN | Normal | Allowed | Allowed | No override | No |
> | YELLOW | Caution | Allowed (warning flag) | Allowed | No override | No |
> | ORANGE | Restricted | Blocked | Allowed | No override | No |
> | RED | Emergency | Blocked | Allowed | SL moves to breakeven | No |
> | BLACK | Shutdown | Blocked | Allowed (closes only) | SL to breakeven; all positions force-closed at next fill | Yes |"

**[A] Scopes** — symbol/currency-scoped for news (MIS resolves symbols), GLOBAL for BLACK (`09-...:76-92`, `:326`). Data-contract `KillSwitchEvent` carries `currency_scope`, `symbol_scope` (`01-System-Overview/02-data-contracts-overview.md:196-200`).

**[A] Escalate-only automation; human de-escalates** — `09-...:312`:
> "**Escalation monotonicity** | Automated triggers can only escalate level; automated triggers cannot de-escalate. De-escalation always requires manual operator action (with confirmation for RED/BLACK resets)."

**[A] Fail-safe to ORANGE (never GREEN)** — `09-...:130-136`; startup with no persisted state → ORANGE (`:142`). Fail-safe enforced in the **broker adapter** via heartbeat, 5s timeout (`:134`).

**[A] Adapter interaction** — adapter enforces KSA effects; always-armed broker-side hard SL set at order placement independent of the SL/TP authority (`09-...:354-374`).

**[A] Bots never see KSA directly** — `09-...:16`: "it does not speak to bots directly … Bots see the effect as blocked or modified authorizations through their normal subscription channel."

**[B] New-core KSA** — same five levels (DEC-0043); trigger classes scheduled_news/black_swan/connectivity/unknown_state; de-escalation is A1 (human); **BMS owns policy, adapter enforces** (`qmx-new-core.md:54-56`). **[B/C] TIGHTEN is DEAD (DEC-0019); REGION_SHIFT rotation DEAD (DEC-0021)** — `outputs/qml-spec.md:156`.

**Effect-vocabulary note:** there are **three different KSA level vocabularies** in this corpus — see Contradictions.

---

## Topic 11 — Correlation ledger / correlation rules (computed vs enforced)

**[A] Correlation enforced at TWO control points** — `02-Components/01-risk-and-sizing/04-slot-competition-model.md:84-122`:
> Control Point 1 (funding stage): correlated bot deprioritised in slot auction (preventive). Control Point 2 (sizing stage): `correlation_multiplier = max(0.3, 1.0 - correlation_penalty)` (reactive, floor 0.3). Both required (`:115-122`).
Layer-A gap: funding-stage gate was NOT implemented — `02-Components/01-risk-and-sizing/07-known-gaps.md:92-104` (Gap 5, High severity).

**[A] Computed vs enforced:** the `correlation_penalty ∈ [0,1]` is *computed* by a "portfolio correlation service"; *enforced* as a multiplier floor 0.3 (never a hard block) — `02-multiplier-stack.md:136-151`. No standalone "correlation ledger" artifact exists in Layer A.

**[B] New-core: cohort correlation is a MEASURED exam input, plus GAP-0008 cross-book cap** — `.brain/entities/qmx-new-core.md:44-45` (exam measures "cohort correlation"); Exposure Desk v2 / cross-book cap is open GAP-0008 (`.brain/sources/qmx-gitbook-newer-docs.md:48`). So in the new core, correlation is *measured at certification* and *capped by the Exposure Desk* rather than applied as a sizing multiplier (declared-weight stack is dead, DEC-0018).

---

## Topic 12 — Money ladder + R (FORM-0004, FORM-0006, D/B/b/Lbar, seat/offer/take, treasury)

**Two entirely different money models coexist in this corpus.** Layer A = half-Kelly multiplier stack + 6-clamp + 3 slots + equity bands. Layer B = the FORM money ladder with seats/offer/take/treasury. The checklist's FORM-0004/FORM-0006 belong to Layer B.

### [B] The new-core money ladder (matches the checklist's FORM shape) — `.brain/entities/qmx-new-core.md:62-67` VERBATIM:
> "Money ladder per book: cap C=2.5S; runway U=E−K; daily budget D=U/n (n=5); `offer_per_seat = D/(B·b·Lbar)`; **`take_per_seat = min(offer, trust_bounded_cost_aware_kelly)`** — "the book offers; trust-bounded cost-aware Kelly disposes." Risk seats: `max_concurrent_live_bots = 3` (ENH-0007). Declared-weight multiplier stacks are on the dead list (DEC-0018)."

Variable meanings as recorded in this corpus:
- **S** = seed = $500; **K** = kill-line = $200; **C** = cap = 2.5×S; **E** = equity; **U** = runway = E−K; **D** = daily budget = U/n, n=5; **B** = (consecutive-stop-out / breaker counter — see below); **b** = daily-budget shaping factor; **Lbar** = characteristic mean loss in R, **measured per bot at exam** (`.brain/entities/qmx-new-core.md:46-49`, `:62-67`; `outputs/clash-report-sltp-vs-book.md:19-22`).
- **`offer_per_seat = D/(B·b·Lbar)`** is the checklist's **FORM-0004** analogue (`offer_R_usd = D/(B*b*Lbar)`). The exact FORM-numbering (FORM-0001..0010) is named but not enumerated in my corpus except: **money ladder = FORM-0001..0005** (`outputs/clash-report-backtest-replay.md:43`: "money ladder (FORM-0001..0005)"). **FORM-0006 / `R_max_usd ≤ B*b*Lbar` is NOT stated verbatim in my corpus** — see Not-found.

**[C] B = consecutive-stop-out breaker counter (scalper book)** — `outputs/clash-report-sltp-vs-book.md:19-22`:
> "**Scalper book**: "benches after consecutive stop-outs" — `registry:scalper_breaker_threshold` = consecutive stop-outs to paper (DEC-0032); `registry:scalper_mean_loss_r` (Lbar) is `kind: measured`, measured per bot at exam; money ladder DEC-0030; budget drain DEC-0031."

**[B] Treasury seed→cap + sweep + distinct capital concepts** — `.brain/entities/qmx-new-core.md:46-49` (quoted Topic 5): cycle = seed→cap; **sweep at rollover only**; equity resets to seed; money ratchets between cycles; knowledge persists (L5). L4: unclaimed budget never redistributed in-cycle (`:92`). DEC-0020: no top-up; no inter-cycle compounding (`outputs/qml-spec.md:155`).

**[C] seat/offer/take mechanics** — `outputs/qml-spec.md:151`: "Risk seats: `max_concurrent_live_bots=3`; `offer_per_seat=D/(B·b·Lbar)`; `take=min(offer, trust-bounded cost-aware Kelly)`; Treasury cycles + Exposure Desk". "the book offers; trust-bounded cost-aware Kelly disposes" (`qmx-new-core.md:64-66`).

### [A] The OLD money model (superseded lineage — original intent) — for contrast:
- Half-Kelly base × 9 multipliers, then 6-operand min-clamp — `02-Components/01-risk-and-sizing/01-canonical-formula.md:78-121` VERBATIM:
> "`raw_kelly = ((net_RR + 1) × win_rate - 1) / net_RR` ; `base_kelly = max(0, raw_kelly) × 0.5`"
> 6-clamp: `min(candidate_risk_pct, family_slot_cap, tier_kelly_cap, account_open_risk_remaining, family_budget_remaining, daily_loss_remaining)`.
- Fee-viability gate `if fee_adjusted_RR < 1.1: block` (`01-canonical-formula.md:70-72`).
- The "absent seventh operand" `session_budget_remaining` deliberately excluded — "compounding is the edge" (`00-overview.md:46`, `01-canonical-formula.md:135-137`).
- Equity bands Growth/Scaling/Guardian with daily loss limits 10%/5%/3% (the "357 rule" — `01-System-Overview/01-system-overview.md:15`) — `03-equity-bands-and-tiers.md:21-25`.
- **3 fixed slots**, not seats — `04-slot-competition-model.md:24`: "`slot_count = 3    -- fixed; does not increase with equity`".
- **[C] ALL of this is DEAD/REPLACED** — `outputs/qml-spec.md:152`: "DPR multiplier + declared-weight multiplier stack … **DEAD** (DEC-0018)"; `backtest-engine-spec.md:39`: "Six-clamp + equity bands + multiplier stack + slot caps [ALL DEAD/REPLACED → money ladder + doors]".

---

## Topic 13 — Stop-out (definition; breakeven-exit ambiguity; consecutive-stop-out counter B=2)

**[A] "Stop-out" loss units** — `02-Components/03-execution-safety-and-asymmetric-sl-tp.md:28-34` (P&L ladder, quoted Topic 6): reversal to BE = **0R loss unit**; reversal to original stop = **1R loss unit**. The one-shot-BE design deliberately lets true losers hit the FULL 1R so the breaker signal stays calibrated (`03-...:24-25`, `06-kill-switch-and-sl-tp-integration.md:122-127`).

**[C] The breakeven-exit ambiguity — EXPLICIT, unresolved ruling** — `outputs/clash-report-sltp-vs-book.md:36-45`:
> "**The breaker counts "stop-outs" — but stop policy DEFINES what a stop-out is.** … Question the new docs cannot answer: *does a breakeven exit count toward `scalper_breaker_threshold`?* If yes — benching accelerates wildly (BE-outs are common for scalpers). If no — the one-shot-BE design quietly reduces breaker sensitivity … **Either answer changes book behavior; neither is written down. This must be a ruling, not an inheritance.**"
Recommendation recorded (`:96-100`, decision D2): "**no** for the scalper book — count full stops only, keep BE-outs as a separate measured metric."

**[C] Consecutive-stop-out counter → benches to paper** — `outputs/clash-report-sltp-vs-book.md:19-20`: "benches after consecutive stop-outs — `registry:scalper_breaker_threshold` = consecutive stop-outs to paper (DEC-0032)." This is the new-core **B** in `offer_per_seat = D/(B·b·Lbar)`.
**[A] The old analogue = CB two-strike counter (B=2)** — `02-Components/02-circuit-breaker-policy-engine.md:18-22`: first CB hit tolerated, **second hit in rolling (10-session daily) window → demote to paper**; reset at daily rollover. The specific value "B=2" as a *money-ladder* variable is Layer-B/registry (`scalper_breaker_threshold`, value not stated in my corpus) — the "2" I can cite verbatim is the CB two-strike threshold (Layer A).

---

## Topic 14 — Alpha-decay evidence classes; "the Book sets the bar" / qualification / exam certificates / certified footprint

**[A] The old system NEVER defined a decay formula** — `outputs/alpha-decay-spec.md:36-39`:
> "⚠️ **No formula, weights, lookback lengths, or numeric thresholds are published anywhere in the vault.** … Whoever implements this defines the actual math — extraction cannot supply it because it never existed on paper."

**[A/C] Four old evidence classes** — `outputs/alpha-decay-spec.md:26-34`:
> "1. **Rolling CB-fire density** … 2. **MAE/MFE drift** … 3. **DPR drawdown context** … 4. **Regime/session overlays**." Triage outcomes: keep / reduce_weight (soft) / demote_to_demo (hard) / retire (hard `WF3_PRUNE`) / rehab_spawned (`:60-72`).

**[C] Two of four classes reference DEAD machinery** — `outputs/clash-report-alpha-decay.md:23-26`: CB-fire density → CB gone (analogue = leash-event frequency, GAP-0012); DPR drawdown → no DPR exists. Surviving classes: MAE/MFE drift, regime/session overlays.

**[B] "The Book sets the bar" — Examination Engine certifies a footprint** — `.brain/entities/qmx-new-core.md:41-45`:
> "**Examination Engine** (COMP-EXAM) — certifies a bot *against a specific book contract* (DEC-0055); gates only on edge-after-cost + non-fiction (DEC-0036); everything else is measured input (Lbar, fire-rate bands, regime-conditional EV, cohort correlation). Exam/live labeler versions must match (L10)."

**[C] The clean new decay definition** — `outputs/clash-report-alpha-decay.md:65-73`:
> "**Alpha decay = sustained, measured divergence of a bot's live footprint from its certified footprint, and/or measured approach toward its charter's death condition.**" DEC-0018-clean; baseline = exam certificate; death conditions live in charters; L16 sunset review = constitutional home for "pointlessness."

**Qualification metrics / exam battery numbers (ratified in registry)** — `outputs/backtest-engine-spec.md:85-87` and `clash-report-backtest-replay.md:64-68`:
> "WF 6mo IS/1mo OOS, ≥200 OOS trades/window, OOS EV floor 0.15R, MC 1000 shuffles, PBO pass<0.25/dead>0.50 — the registry values are the binding parameterization."

**[A] Old qualification: DPR composite [0,100], six weighted dimensions → T1/T2/T3** — `02-Components/06-performance-rating-service.md:26-41` (weights 25/20/20/10/15/10; T1 80–100, T2 50–79, T3 0–49). **[C] This composite is a DEC-0018 violation ("opinions wearing math") — do not port** (`outputs/clash-report-bot-rating.md:38-41`).

---

## Topic 15 — Book/BMS validation leads (how a NEW Book/BMS proves itself before carrying money)

**[B] The new-core front door = the Examination Engine certifying against a specific book contract** (`qmx-new-core.md:41-45`, quoted Topic 14). Gates only on **edge-after-cost + non-fiction** (DEC-0036); everything else measured. Certification container = MIS-Archive + EXAM + QML (`qmx-new-core.md:76-77`).

**[C] Replay/parity is the validation spine** — `outputs/backtest-engine-spec.md:20-32`:
> "**Parity is the load-bearing constraint** … The only two permitted substitutions: (1) data source … (2) execution layer … Everything else identical — *including known production gaps*."
Reproducible from exactly four keys: `bot_spec_version`, `data_snapshot_id`, `config_hash`, `seed` (`backtest-engine-spec.md:110-116`).

**[C] Statistical battery** — walk-forward (expanding/rolling), Monte Carlo N=1000, PBO via CSCV (S=16; bands <0.25 low / 0.25–0.50 moderate / >0.50 do-not-promote) — `backtest-engine-spec.md:69-87`.

**[C] New-core validation = one shared Replay Service, two customers (Exam + agents), book-profile-aware** — `outputs/clash-report-backtest-replay.md:72-96`: "a backtest is against a BOOK, not just a bot"; certification queue prioritised over exploration; every refusal signs a replay veto ledger.

**[A] Old promotion ramp (the donor discipline):** POST_WF2 → PAPER_TRADING → LIVE(probation, Kelly-discounted) → LIVE(full), with manual approval gate at the paper→live boundary (`02-Components/07-bot-registry-and-lifecycle.md:127-141`; `08-paper-trading-demotion-service.md:62-73`).

**BMS self-validation:** **NOT FOUND** — no lead in this corpus for how a *BMS* (as opposed to a book/bot) proves itself.

---

## Topic 16 — Same-tick priority; no-overnight; hold limits; dead-zone (~45min)

**[A] Old same-tick priority (fully specified, donor model)** — `02-Components/06-kill-switch-and-sl-tp-integration.md:13-25`:
> "Kill Switch Authority (highest priority — always wins) ↓ SL/TP Service ↓ Risk Engine Output ↓ Execution." Kill-switch read is the FIRST check in the position-monitoring loop (`:46-74`); `AmendInstruction.priority`: kill-switch=0 supersedes normal=10 (`03-...sl-tp.md:60-71`).

**[C] New-core same-tick priority among protective stops / force-flat / KSA / fast-invalidation is UNDEFINED — flagged for ruling** — `outputs/clash-report-sltp-vs-book.md:55-63`:
> "**Two authorities can now close positions — priority is undefined.** … KSA effects enforced by the adapter AND the leash's **hold-time force-flat** — but nothing defines how force-flat, KSA closures, and any SL/TP amendments interleave on the same tick, or who wins."
Recommended (decision D4, `:102-104`): "**KSA ≥ force-flat ≥ stop amendments, adapter-enforced** … write it into the leash spec." Also: TIGHTEN dead (DEC-0019) so the old override list must be pruned (`:63`, `sltp-authority-spec.md:70-76`).

**[B] Hold-time force-flat & no-overnight analogue** — the leash chain's final rung is **hold-time force-flat** (`qmx-new-core.md:38-40`); this is the new-core's position-time-limit / no-overnight organ. Explicit "no-overnight policy" wording is **NOT FOUND**; the closest is (a) leash hold-time force-flat and (b) Layer-A OVERNIGHT dead-zone advice.

**[A] Dead-zone** — `02-Components/01-risk-and-sizing/05-session-architecture.md:32`: "OVERNIGHT | 19:00–20:00 | None | No | Dead zone — no new positions advised" (a **1-hour** window, not ~45 min). Old WF3 pool-cleaning ran in the dead zone precisely because no auction ran there (`outputs/alpha-decay-spec.md:9-16`, `clash-report-alpha-decay.md:51-55`). The specific "~45min session-handover no-trade" is **NOT FOUND** — this corpus's dead zone is the 1h OVERNIGHT window. **[C] the dead-zone rationale evaporates in the new core** (scheduled reckoning points replace it) — `clash-report-alpha-decay.md:51-55`.

**[A] Session-warmup entry gate (adjacent to hold limits)** — `05-session-architecture.md:245-279`: LONDON_NY_OVERLAP `warmup_seconds=1500` (25 min), `warmup_dominant_family=ORB`; house money disabled during overlap warmup; rejection code `SESSION_WARMUP`.

---

## Topic 17 — Multi-currency (numeraire, cross-account aggregation, FX conversion for risk math)

**Almost entirely NOT FOUND.** This corpus assumes a single account base currency and never specifies cross-account aggregation or FX conversion for risk math.

**[A] Single base-currency convention** — `01-System-Overview/02-data-contracts-overview.md:245`: "All monetary fields are in account base currency unless stated otherwise."
**[A] AccountProfile carries one ISO-4217 currency, used for pip-value calc** — `bmad-docs/planning-artifacts/qml-types-catalogue.md:1779,1795`: "`currency: str … Account base currency (ISO 4217)` … Read-by Risk (pip value calc)."
**NOT FOUND:** account numeraire selection, cross-account/cross-book aggregation, FX conversion for risk math. The new-core treasury math (S/K/C/E/U/D) is stated in bare USD ($500/$200) with no FX layer (`qmx-new-core.md:46-49`). GAP-0008 (cross-book cap) is open but says nothing about currency.

---

## Contradictions section

1. **THREE kill-switch level vocabularies coexist:**
   - Five-level GREEN/YELLOW/ORANGE/RED/BLACK — canonical KSA spec `02-Components/09-kill-switch-authority.md:26-32`; data contract `01-System-Overview/02-data-contracts-overview.md:195`; new-core `qmx-new-core.md:54` (DEC-0043).
   - Six-level MONITOR/TIGHTEN/BREAKEVEN/FLATTEN_NEW/FLATTEN_ALL/HARD_STOP — risk-integration doc `02-Components/01-risk-and-sizing/06-kill-switch-and-sl-tp-integration.md:37-42`.
   - Four-level news enum NONE/TIGHTEN/HALT_ENTRIES/FLATTEN — MIS snapshot `02-Components/04-market-intelligence-service.md:267,326-331`.
   Resolution recorded by corpus: new core keeps the five levels and **kills TIGHTEN (DEC-0019)** (`outputs/qml-spec.md:156`), so all three lists are partly superseded.

2. **Money model contradiction (old vs new):** half-Kelly 9-multiplier stack + 6-clamp + 3 fixed slots + equity bands (`02-Components/01-risk-and-sizing/*`) vs the FORM money ladder `offer=D/(B·b·Lbar)` + seats + treasury cycles (`qmx-new-core.md:62-67`). Corpus rules the old model **DEAD** (DEC-0018) — `outputs/qml-spec.md:152`, `backtest-engine-spec.md:39`.

3. **Clamp operand count:** `00-overview.md:125` explicitly repudiates an even-older 7-operand clamp ("Any planning document that shows seven clamp operands reflects an older design; this spec supersedes it"). So even within Layer A there is a 6-vs-7 lineage.

4. **DPR consumer contradiction:** old DPR/PRS feeds slot auction + CB + demotion (`06-performance-rating-service.md`), but the new core has "no tier field, no tier consumer, and its sizing formula has no merit input — by ruling" (`outputs/clash-report-bot-rating.md:52-55`). Do-not-port.

5. **"Canonical" labels are void:** every old-vault file self-labels "Canonical v1.0/v2.0"; the 2026-07 layers state that label "carries no authority now" (`outputs/*` headers). An internal authority contradiction the reader must resolve by date, not by the label.

6. **Exit ownership is a hole, not a decision:** old vault gives a full system-owned SL/TP Authority; new core has no stop component and no ruling on who owns exits or same-tick close priority (`outputs/clash-report-sltp-vs-book.md:7-10,55-63`). Genuinely unresolved.

7. **Dead-zone duration:** Layer A = 1h OVERNIGHT window (`05-session-architecture.md:32`); checklist's "~45min session-handover" not present. And the new core removes the dead-zone rationale entirely (`clash-report-alpha-decay.md:51-55`).

---

## Not-found list (checklist topics with NO / only-partial evidence in this corpus)

- **Topic 1 — CT-BOOK-01/02 field-level schema:** NOT FOUND (only prose "pod with charter, capital, roster, profile, rules, journals" + contract *names*). No versioned book-type field schema.
- **Topic 2 — CT-BMS-01..05 field-level schema:** NOT FOUND (only the four-desk names + ownership rules).
- **Topic 3 — Book↔BMS numeric multiplicity; Book↔account/venue (one Book binding accounts at several venues):** NOT FOUND. Only bot↔Book ≤3 concurrent live bots is stated.
- **Topic 4 — seat-state enum / book-mode enum / seat-state-vs-book-mode split:** NOT FOUND as such (only bot lifecycle states + `account_mode` LIVE/DEMO, which the corpus says must be re-derived onto treasury cycles/leash rungs).
- **Topic 5 — "scalping-book-v2 = NEW Book, never inherits v1 ledger" ruling:** NOT FOUND verbatim (supporting primitives only: BotSpec immutability; treasury "no inter-cycle compounding").
- **Topic 12 — FORM-0006 `R_max_usd ≤ B*b*Lbar` verbatim:** NOT FOUND. `offer_per_seat=D/(B·b·Lbar)` (FORM-0004 analogue) IS present; money ladder is labeled FORM-0001..0005 (`clash-report-backtest-replay.md:43`); FORM-0001..0010 exist by name only. Exact per-FORM bodies are in the GitBook registry, not this corpus.
- **Topic 15 — how a BMS (not a bot/book) validates itself:** NOT FOUND.
- **Topic 16 — explicit "no-overnight policy" wording; explicit hold-limit numbers; "~45min" session-handover dead-zone:** NOT FOUND (closest: leash hold-time force-flat; 1h OVERNIGHT dead-zone; 25-min overlap warmup).
- **Topic 17 — account numeraire selection, cross-account/cross-book aggregation, FX conversion for risk math:** NOT FOUND (only single-base-currency convention + ISO-4217 field for pip-value calc).
