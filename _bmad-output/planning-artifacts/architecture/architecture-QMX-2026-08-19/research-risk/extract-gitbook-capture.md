# QMX Risk-Sitting Extract — GitBook Capture (2026-07-18)

**Extractor corpus:** `C:/Users/Mubarak/Documents/QMX/raw/online/qmx-gitbook/captures/2026-07-18T141659Z/pages/markdown/` (67 markdown pages).
**Corpus layer:** GitBook snapshot, capture timestamp `2026-07-18T14:16:59Z`. This is the **ratified Book/BMS baseline (DEC-0002)** per the fan-out charter. Internal dates inside the corpus: ADRs ratified **2026-07-08**; changelog "Operator Rulings Applied" pass **2026-07-08**; live GitBook host `elios-1.gitbook.io/qmx`.
**Precedence note:** I do NOT decide precedence. Every finding below is labeled with this single corpus layer (GitBook 2026-07-18). Where the reader must rank against Desktop/QMX rulings, old wiki, or QMX-discussion, that is the reader's job.

**Capture integrity:** Two capture directories exist — `2026-07-18T140822Z` and `2026-07-18T141659Z`. They are **byte-identical** (both 207,519 bytes across 67 pages; `diff -rq` returns no differences). I cite the later timestamp `...141659Z`. All citations below are `path:line` **relative to** the corpus base above (drop the boilerplate GitBook footer that begins at each file's `# Agent Instructions` line — that footer is inert platform text, not QMX content).

**Citation shorthand:** `components/book-template.md:28` == `<base>/components/book-template.md` line 28.

---

## Topic 1 — Book schema: fields, versioned book-type schema, the seven doors

**Book-type schema fields (CT-BOOK-01 Trade Intent Envelope) — VERBATIM** (`contracts/ct-book-01-trade-intent-envelope.md:7-24`). Note: this is the **bot→book trade-intent** contract, not a "book record" schema; the corpus has no standalone "book object" field list — a Book is defined by its parts (charter/capital/roster/profile/rules/journals, see glossary below).

```yaml
id: CT-BOOK-01
title: Trade Intent Envelope
status: reviewed
decisions: [DEC-0002, DEC-0035]
fields:
  book_id: {type: string, required: true}
  bot_id: {type: string, required: true}
  pair: {type: string, required: true}
  side: {type: enum, values: [BUY, SELL], required: true}
  requested_r: {type: number, units: R, required: true}
  footprint_version: {type: string, required: true}
  snapshot_version: {type: string, required: true}
  timestamp_utc: {type: string, format: date-time, required: true}
rules:
  - "The bot emits intent; book infrastructure runs doors and sizing."
  - "Every refusal emits CT-BMS-05."
```

**What a Book IS (glossary, VERBATIM)** — `glossary.md:11`: "**Book**: A pod with charter, capital, roster, profile, rules, and journals. A book controls bots and never trades directly. DEC-0002."

**Charter grammar — four slots** (`components/book-template.md:26`): "Every charter fills four slots: **game played, money shape, customer plus headline metric, and death condition**. DEC-0027."

**The seven doors — VERBATIM** (`components/book-template.md:28`): "The seven doors are **footprint, viability veto, R_max, daily budget, breaker, exposure ledger, and kill switch**. DEC-0035."
- Door ordering pipeline (mermaid, `components/book-template.md:43`): `intent --> footprint --> viability --> rmax --> budget --> breaker --> exposure --> ksa --> adapter`.
- Book-template authority "May" grammar (`components/book-template.md:11`): "define charter grammar, footprint grammar, money-rule grammar, entrance-exam requirements, leash chain, and capacity/sweep mechanics." "May never: trade directly … DEC-0002, DEC-0005, DEC-0024, DEC-0025" (`:13`).
- **Template vs instance split** — template documented once as **sealed Sections 0-5**; scalper documented separately as first instance; infrastructure after Section 5 is global multi-book capability (`decisions/adr-0002-template-and-instance-split.md:20`, dated 2026-07-08; DEC-0026, DEC-0003).
- Book Template interfaces (`components/book-template.md:17-22`): Trade intent in CT-BOOK-01 (Bot runtime); Book mode out CT-BOOK-02 (COMP-BMS); Exam certificate in CT-EXAM-01 (COMP-EXAM); MIS snapshot in CT-MIS-01 (COMP-MIS-LIVE).
- **"Book Section 6" is an open gap** — GAP-0001 workspace design; FM-4 "Book Section 6 is requested → Mark GAP(GAP-0001) and do not invent workspace behavior" (`components/book-template.md:64`; `gap-report.md:13`).

No explicit "CT-BOOK-03" exists in this corpus (only CT-BOOK-01 and CT-BOOK-02; see `contracts.md` / `architecture/dependency-graph.md:25`).

---

## Topic 2 — BMS schema: fields, what BMS owns vs what the Book owns

**BMS definition & desks (VERBATIM)** — `components/book-management-system.md:7`: "BMS accounts for and constrains books. It has **Treasury, Exposure, Records, and Reporting desks**, and it never trades, sizes, or reaches inside a book. DEC-0045." Glossary confirms same four desks (`glossary.md:9`).

**BMS authority boundary (VERBATIM)** — `components/book-management-system.md:11`: "May: own **virtual ledger state, exposure measurement, mode registry, append-only journals, reporting metrics, KSA policy, and news block directives**." `:13`: "May never: trade directly, mutate bot logic, overwrite journals in place, or bypass the veto ledger. DEC-0002, DEC-0012, DEC-0046."
- Records is append-only and owns the ONLY journal write path; Reporting computes from Records with **zero authority** (`components/book-management-system.md:41`, DEC-0046).
- GAP-0008: Exposure Desk v2 authority open, **including cross-book cap authority** (`components/book-management-system.md:43`, `:50`).

**BMS owns 5 contracts (CT-BMS-01..05).** The BMS-owned schemas, VERBATIM:

CT-BMS-01 Treasury Event (`contracts/ct-bms-01-treasury-event.md:7-22`):
```yaml
id: CT-BMS-01
title: Treasury Event
status: reviewed
decisions: [DEC-0038]
fields:
  event_id: {type: string, required: true}
  book_id: {type: string, required: true}
  cycle_id: {type: string, required: true}
  event_type: {type: enum, values: [sweep, refund, re_seed], required: true}
  amount: {type: number, units: USD, required: true}
  reason: {type: string, required: true}
  occurred_at_utc: {type: string, format: date-time, required: true}
rules:
  - "Only these three event types cross the book-to-treasury boundary."
```

CT-BMS-02 Mode Registry Read (`contracts/ct-bms-02-mode-registry-read.md:7-18`):
```yaml
id: CT-BMS-02
title: Mode Registry Read
status: reviewed
decisions: [DEC-0045]
fields:
  book_id: {type: string, required: true}
  mode: {type: enum, values: [LIVE, PAPER, BENCHED, STOOD_DOWN], required: true}
  updated_at_utc: {type: string, format: date-time, required: true}
rules:
  - "The BMS mode registry is the authoritative mode map."
```

CT-BMS-03 Reconciliation Report (`contracts/ct-bms-03-reconciliation-report.md:7-20`):
```yaml
id: CT-BMS-03
title: Reconciliation Report
status: reviewed
decisions: [DEC-0015]
fields:
  account_id: {type: string, required: true}
  virtual_equity: {type: number, units: USD, required: true}
  broker_equity: {type: number, units: USD, required: true}
  explained_delta: {type: number, units: USD, required: true}
  verdict: {type: enum, values: [reconciled, drift, unknown], required: true}
rules:
  - "Unexplained drift is a technical kill."
```

CT-BMS-04 News Block Directive (`contracts/ct-bms-04-news-block-directive.md:7-21`):
```yaml
id: CT-BMS-04
title: News Block Directive
status: reviewed
decisions: [DEC-0010, DEC-0044]
fields:
  directive_id: {type: string, required: true}
  affected_currency: {type: string, required: true}
  affected_pairs: {type: array, required: true}
  window_start_utc: {type: string, format: date-time, required: true}
  window_end_utc: {type: string, format: date-time, required: true}
  reason: {type: string, required: true}
rules:
  - "Directive applies to live and paper books."
```

CT-BMS-05 Journal Append (`contracts/ct-bms-05-journal-append.md:7-21`):
```yaml
id: CT-BMS-05
title: Journal Append
status: reviewed
decisions: [DEC-0012, DEC-0046]
fields:
  journal: {type: string, required: true}
  event_id: {type: string, required: true}
  event_type: {type: string, required: true}
  payload: {type: object, required: true}
  refs: {type: array, required: true}
  occurred_at_utc: {type: string, format: date-time, required: true}
rules:
  - "Corrections append new entries that reference corrected entries."
```

**BMS-owned journals (logging-spec, VERBATIM table)** — `lenses/logging-spec.md:13-17`: Veto ledger (COMP-BMS), KSA audit log (COMP-KSA/COMP-BMS), Trade journal (COMP-BMS), Book journal (COMP-BMS: "Mode changes, leash events, cycle events"), Correlation ledger (COMP-BMS: "Chorus observations and cohort references").

**Book-vs-BMS split (authority hierarchy, VERBATIM)** — `system-constitution.md:47`: "The book owns admission, sizing, doors, leash, and profile selection. BMS owns accounting, constraints, journals, KSA policy, and reporting." L1 (`:11`): "Bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market. DEC-0002."

---

## Topic 3 — Cardinalities (Book↔BMS, bot↔Book, Book↔account/venue)

Corpus states these only **indirectly**; no explicit multiplicity numbers except the live-bot cap.

- **BMS↔Book:** BMS "accounts for and constrains **books**" (plural) and owns a **mode registry** mapping `book_id → mode` (`components/book-management-system.md:7`; `contracts/ct-bms-02-mode-registry-read.md:16` "authoritative mode map"). Implies **one BMS governs many Books**. No statement that a Book owns "several BMS" — architecture shows a single COMP-BMS (`architecture/overview.md:38-69`; `architecture/dependency-graph.md:57`). **Cross-book cap authority is explicitly a GAP** (GAP-0008, `components/book-management-system.md:43`).
- **bot↔Book:** A Book is "A pod with … roster …" and "controls bots" (plural) (`glossary.md:11`). Bot "is validated against the book contract it applies to join" (`components/examination-engine.md:7`, DEC-0055) — a bot joins a specific book. Scalper caps concurrency: `max_concurrent_live_bots` **N_live_max = 3** (`registry/variables.md:114-122`, DEC-0028, ENH-0007). So **one Book → many bots, ≤3 live at once (scalper instance value)**.
- **Book↔account/venue:** Account binding lives at the **adapter**, not the Book: `account_binding: {type: string, required: true}` in CT-ADAPTER-01 (`contracts/ct-adapter-01-broker-adapter-command.md:15`); adapter "maintain[s] account binding" (`components/broker-adapter.md:11`). Reconciliation is per `account_id` (`contracts/ct-bms-03-reconciliation-report.md:13`). **No statement that one Book binds accounts across several venues** — the single broker shown is "Broker / cTrader Open API" (`architecture/overview.md:14`); multi-venue binding is **not addressed** (see Not-found).

---

## Topic 4 — Book/BMS lifecycle states & modes; seat-state vs book-mode split

**Book mode enum (VERBATIM, CT-BOOK-02)** — `contracts/ct-book-02-book-mode-state.md:7-22`:
```yaml
id: CT-BOOK-02
title: Book Mode State
status: reviewed
decisions: [DEC-0014, DEC-0037]
fields:
  book_id: {type: string, required: true}
  mode: {type: enum, values: [LIVE, PAPER, BENCHED, STOOD_DOWN], required: true}
  reason: {type: string, required: true}
  trigger_decision: {type: string, pattern: "DEC-[0-9]{4}", required: true}
  effective_at_utc: {type: string, format: date-time, required: true}
rules:
  - "Paper balances freeze at mode flip."
  - "Breaker bench-to-paper auto-resets at next open under DEC-0032."
  - "Other paper/live promotion, freeze, demotion, and return semantics remain GAP-0006."
```

- **The mode enum `[LIVE, PAPER, BENCHED, STOOD_DOWN]` recurs identically** in CT-BOOK-02, CT-BMS-02 (`:14`), and CT-PAPER-01 `from_mode`/`to_mode` (`contracts/ct-paper-01-paper-mode-transition.md:15-16`).
- **Authoritative mode map lives in the BMS mode registry** (CT-BMS-02, `:16`).
- **Seat-state vs book-mode split:** the corpus does NOT enumerate a separate "seat state" enum. It splits **book mode** (above) from the **leash chain** (per-event escalation rungs) and the **KSA level** (global protection). "Seat" language appears only as "offer risk seats" / "live seat" / "take_per_seat" in sizing (`components/scalper-book.md:11`, `:39`; `registry/formulas.md:41`). A bot benches **to paper** after consecutive stop-outs (`components/paper-mode-system.md:24`). **No dedicated seat-state enum found** (see Not-found).
- **KSA levels (separate enum):** `[GREEN, YELLOW, ORANGE, RED, BLACK]` (`components/kill-switch-authority.md:25`, DEC-0043; `registry/variables.md:222-230`).

---

## Topic 5 — Book versioning + compatibility (e.g. scalping-book-v2 = new Book, no ledger inheritance)

**Not found as an explicit rule in this corpus.** There is NO statement equivalent to "scalping-book-v2 is a NEW Book that never inherits v1 ledger."
- The version fields that DO exist are **footprint/snapshot/labeler** versions, not book-type versions: `footprint_version`, `snapshot_version` (CT-BOOK-01, `:18-19`); `snapshot_version` and `labeler_versions` (CT-MIS-01 `:15`, CT-EXAM-01 `:15`, CT-MIS-02 `:17`); "Labeler version changes → Certificate parity requires re-certification" (`components/market-intelligence-service.md:56`, DEC-0011).
- The nearest structural analog is the **template/instance split** (`decisions/adr-0002-template-and-instance-split.md`): each book instance "owns its values"; the dead idea "uniform values across books" (DEC-0024) forbids reusing one book's values as another's. But book-type **versioning / ledger-inheritance** is not spelled out. (See Not-found.)

---

## Topic 6 — Exit ownership (bots own exit organs vs Book owns exits; forced exits; fast invalidation; dynamic SL/TP)

- **Bots own exit organs (VERBATIM)** — `glossary.md:13`: "**Bot**: The only market-touching actor. A bot owns **entry logic and exit organs** while book infrastructure owns admission and sizing. DEC-0002." Constitution `:47`: "The bot owns market-facing **entry and exit organs**."
- **Book/BMS forced-exit path = the leash chain (VERBATIM)** — `components/book-template.md:30`: "The leash chain escalates through **ambient governor, day closure, bench-to-paper, chorus flag, kill-line stand-down, classed kill switch, and hold-time force-flat**. DEC-0037." The terminal rung "**hold-time force-flat**" is the forced flatten.
- **KSA reaches positions only via adapter effects** — `close_position` and `close_all` are adapter command types (CT-ADAPTER-01 `:15`, see Topic 10).
- **Graduated-vs-instant law** — `system-constitution.md:33` L12: "Graduated policy shrinks before it blocks unless the event class demands instant action. DEC-0013."
- **NOT found:** dynamic SL/TP mechanics (who moves stops, when), "fast invalidation" as a named organ, position-safety / SL-TP authority split. A whole-corpus grep for `stop loss|take profit|SL|TP|invalidat|position-safety` returns only "certificate invalidates" (`components/examination-engine.md:55`) — unrelated. (See Not-found.)

---

## Topic 7 — Paper mode

**Paper Mode System (VERBATIM behavior)** — `components/paper-mode-system.md:7`: "Paper mode is diagnostic. It **freezes the counterfactual balance at flip** and preserves evidence after a breaker, kill-line stand-down, or demotion. DEC-0014."
- May/May-never (`:11-13`): "May: represent paper mode, freeze balances, keep sensing and paper trading on, and emit transition records." "May never: hand-adjust paper balance, revive the dead live-restart-from-remnant path, or treat paper gains as treasury cash. DEC-0014, DEC-0023."
- **Bench-to-paper trigger** (`:24`): "After `registry:scalper_breaker_threshold` consecutive stop-outs, the affected bot **benches to paper for the rest of the day and auto-resets at next open**. DEC-0032."
- **State transitions (mermaid, `:29-34`):** `LIVE --> PAPER: breaker bench-to-paper DEC-0032`; `PAPER --> LIVE: breaker auto-reset at next open DEC-0032`; `PAPER --> STOOD_DOWN: dead remnant restart path DEC-0023`.
- **CT-PAPER-01 transition schema (VERBATIM)** — `contracts/ct-paper-01-paper-mode-transition.md:7-22`:
```yaml
id: CT-PAPER-01
title: Paper Mode Transition
status: reviewed
decisions: [DEC-0014, DEC-0032]
fields:
  book_id: {type: string, required: true}
  bot_id: {type: string, required: false}
  from_mode: {type: enum, values: [LIVE, PAPER, BENCHED, STOOD_DOWN], required: true}
  to_mode: {type: enum, values: [LIVE, PAPER, BENCHED, STOOD_DOWN], required: true}
  frozen_balance: {type: number, units: USD, required: true}
  trigger_event_id: {type: string, required: true}
rules:
  - "Paper balance is frozen at flip and is never hand-adjusted."
  - "Only the breaker auto-reset path is ratified; other transition semantics remain GAP-0006."
```
- **Evidence comparability / news protection over paper (VERBATIM)** — SCN-0003 `scenarios/scn-0003-news-block.md:19`: "Both entries are refused… **no paper data is collected under a known invalid news window**. DEC-0010." L9 (`system-constitution.md:27`): news pairs blocked for all books "in live and paper mode."
- **NOT found:** "bench-to-paper" paired-demo bindings, duplicate-order prevention, comparability metric mechanics. The complete paper/live transition state machine (promotion, freeze, demotion, non-breaker return) is **GAP-0006** (`components/paper-mode-system.md:27`, `:36`; CT-BOOK-02 rule `:21`; `gap-report.md:17`). Only the breaker auto-reset path is ratified. (See Not-found for paired demo bindings / duplicate-order prevention.)

---

## Topic 8 — News protection (windows, severity tiers, currency→instrument mapping, open positions, overrides)

- **CT-BMS-04 News Block Directive** carries `affected_currency` (string) + `affected_pairs` (array) + `window_start_utc` + `window_end_utc` + `reason` (VERBATIM schema in Topic 2). This IS the currency→instrument mapping mechanism: a currency maps to a set of affected pairs, bounded by an explicit UTC window. Rule: "Directive applies to live and paper books." (`contracts/ct-bms-04-news-block-directive.md`).
- **Law (VERBATIM)** — `system-constitution.md:27` L9: "News-affected currency pairs are blocked for all books in live and paper mode. DEC-0010."
- **KSA trigger class `scheduled_news`** — CT-KSA-01 `trigger_class` enum includes `scheduled_news` (`contracts/ct-ksa-01-kill-switch-state-event.md:15`); rule "News-affected currency pairs block live and paper" (`:21`).
- **Emitter:** BMS Exposure desk emits the directive (`scenarios/scn-0003-news-block.md:11`; `components/book-management-system.md:36` mermaid `exposure -->|"CT-BMS-04"| ksa`).
- **NOT found (explicit):** before/after window lengths **in minutes**, **event severity tiers** for news specifically (news is binary block, not tiered), **open-position behavior** during a news window (scenario only tests *new candidate entries* being refused; it does not state what happens to already-open positions), and **overrides**. The window is expressed as start/end UTC timestamps, with no minutes-before / minutes-after constants in the registry. (See Not-found.)

Note: notification **tiers** exist but are for operator alerts, not news severity — CT-NOTIFY-01 `proposed_tier: enum [P1, P2, P3, P4]` (`contracts/ct-notify-01-notification-candidate.md:17`, interim ENH-0001, final = GAP-0002).

---

## Topic 9 — SQS / spread-quality sensing (formula, inputs, thresholds, cadence, hysteresis; and WHY)

**Only the interface surface exists — no formula/threshold/cadence/hysteresis in this corpus.**
- **SQS appears as two MIS-Live snapshot fields (VERBATIM)** — CT-MIS-01 (`contracts/ct-mis-01-mis-live-snapshot.md:20-21`): `sqs_score: {type: number, required: true}` and `sqs_hard_block: {type: boolean, required: true}`.
- **Related spread field (VERBATIM):** `spread_state: {type: enum, values: [normal, elevated, extreme], required: true}` (`contracts/ct-mis-01-mis-live-snapshot.md:16`).
- **SQS behavior / failure semantics (VERBATIM)** — `components/market-intelligence-service.md:26`: "Failure is conservative: failed labelers mark degraded fields, **SQS unreachable creates a hard door block**, and dead feed state prevents new entries. DEC-0042." FM-2 (`:55`): "SQS unreachable → Door performs hard block."
- MIS is information-only (never sizes/blocks/trades); the door consuming SQS enforces (`components/market-intelligence-service.md:7`, DEC-0007/DEC-0040; L6 `system-constitution.md:21`).
- **WHY it existed:** the corpus frames SQS within MIS's spread/liquidity sensing (`spread_state`, `liquidity_stress`, `gap_event` alongside it) as a door input, but gives **no narrative rationale** beyond "conservative failure → hard block." No formula for `sqs_score`, no numeric threshold, no cadence, **no hysteresis** anywhere (whole-corpus grep for `hysteresis` = zero hits). (See Not-found / Contradictions.)

Full CT-MIS-01 snapshot schema (VERBATIM, for context) — `contracts/ct-mis-01-mis-live-snapshot.md:7-28`:
```yaml
id: CT-MIS-01
title: MIS-Live Snapshot
status: reviewed
decisions: [DEC-0007, DEC-0011, DEC-0040, DEC-0041, DEC-0042, DEC-0049]
fields:
  pair: {type: string, required: true}
  resolution: {type: string, required: true}
  snapshot_version: {type: string, required: true}
  spread_state: {type: enum, values: [normal, elevated, extreme], required: true}
  gap_event: {type: boolean, required: true}
  liquidity_stress: {type: boolean, required: true}
  feed_state: {type: enum, values: [fresh, stale, dead], required: true}
  sqs_score: {type: number, required: true}
  sqs_hard_block: {type: boolean, required: true}
  regime: {type: enum, values: [trend, range, chaos], required: false}
  regime_confidence: {type: number, required: false}
  degraded_sensors: {type: array, required: true}
rules:
  - "Snapshot is information-only."
  - "Dead feed state prevents new entries through book profile handling."
```

---

## Topic 10 — Kill switch / KSA (authority, scopes, escalate-only, effect vocabulary, adapter interaction)

- **Authority model (VERBATIM)** — `components/kill-switch-authority.md:7`: "KSA is the global protection state machine. **BMS owns policy, the trading node enforces effects through the adapter, and bots never see KSA directly**. DEC-0008." May-never (`:13`): "**de-escalate automatically**, ask bots to interpret KSA state, or revive the dead half-size-through-bad-conditions level. DEC-0009, DEC-0019."
- **Escalate-only + human de-escalates (VERBATIM)** — `system-constitution.md:25` L8: "Automated KSA transitions escalate only; **de-escalation requires A1 human authority**. DEC-0009." Glossary `glossary.md:7`: "**A1 gate**: Human resurrection authority. A1 governs return-to-live and never performs automatic protection. DEC-0004." KSA rule "Automated transitions escalate only" (`contracts/ct-ksa-01-kill-switch-state-event.md:20`).
- **Levels (5):** `GREEN, YELLOW, ORANGE, RED, BLACK` (`components/kill-switch-authority.md:25`, DEC-0043; enum also `registry/variables.md:224`, `configurable: false`, "Global capability; book profiles select behavior").
- **Trigger classes (4):** `scheduled_news, black_swan, connectivity, unknown_state` (`components/kill-switch-authority.md:25`, DEC-0044; CT-KSA-01 `:15`).
- **CT-KSA-01 schema (VERBATIM)** — `contracts/ct-ksa-01-kill-switch-state-event.md:7-22`:
```yaml
id: CT-KSA-01
title: Kill-Switch State Event
status: reviewed
decisions: [DEC-0009, DEC-0010, DEC-0043, DEC-0044]
fields:
  event_id: {type: string, required: true}
  level: {type: enum, values: [GREEN, YELLOW, ORANGE, RED, BLACK], required: true}
  trigger_class: {type: enum, values: [scheduled_news, black_swan, connectivity, unknown_state], required: true}
  affected_pairs: {type: array, required: true}
  evidence_refs: {type: array, required: true}
  effective_at_utc: {type: string, format: date-time, required: true}
rules:
  - "Automated transitions escalate only."
  - "News-affected currency pairs block live and paper."
```
- **Scope:** CT-KSA-01 scopes by `affected_pairs` (array). News directive scopes by `affected_currency` + `affected_pairs` (CT-BMS-04). KSA level itself is described as **global** protection state (`components/kill-switch-authority.md:7` "global protection state machine"; `registry/variables.md:230` "Global capability"). Corpus does NOT enumerate pair/Book/account/venue/global as a formal scope ladder — only pair-array + global. (Partial; see Not-found for the full scope ladder.)
- **Effect vocabulary / adapter interaction (VERBATIM)** — effects are the **adapter command types**, CT-ADAPTER-01 (`contracts/ct-adapter-01-broker-adapter-command.md:7-21`):
```yaml
id: CT-ADAPTER-01
title: Broker Adapter Command
status: reviewed
decisions: [DEC-0008, DEC-0044]
fields:
  command_id: {type: string, required: true}
  command_type: {type: enum, values: [place_order, cancel_order, close_position, close_all], required: true}
  account_binding: {type: string, required: true}
  payload: {type: object, required: true}
rules:
  - "Bots do not call broker platforms directly."
  - "Unknown state emits trigger_class unknown_state and blocks broker execution until reconciled."
  - "The trigger-to-KSA-level target matrix remains GAP-0015."
```
  KSA→adapter interface: `KSA event out CT-KSA-01 → COMP-ADAPTER` (`components/kill-switch-authority.md:19`; `architecture/overview.md:32` `ksa -->|"state CT-KSA-01"| adapter`).
- **The effect vocabulary "suspend-new / drain / close_all"** as named terms is **NOT** in this corpus — the closest verbs are the adapter command enum (`place_order, cancel_order, close_position, close_all`) plus "block affected pairs" / "blocks broker execution until reconciled" / "hard block" / "prevents new entries." (See Contradictions/Not-found.)
- **Open gap:** the full **trigger-to-level target matrix is GAP-0015** (`components/kill-switch-authority.md:32`, `:38`; FM-1/FM-3 `:50`,`:52`; `gap-report.md:24`). The dead "TIGHTEN half-size kill level" is forbidden (DEC-0019, `dead-decisions.md:12`).

---

## Topic 11 — Correlation ledger / correlation rules (computed vs enforced)

- **Computed:** the **Examination Engine** produces cohort correlation certificates — CT-EXAM-02 (VERBATIM, `contracts/ct-exam-02-cohort-correlation-certificate.md:7-20`):
```yaml
id: CT-EXAM-02
title: Cohort Correlation Certificate
status: reviewed
decisions: [DEC-0036, DEC-0048]
fields:
  cohort_id: {type: string, required: true}
  book_id: {type: string, required: true}
  correlation_observations: {type: array, required: true}
  expected_loss_shape: {type: object, required: true}
  certified_at_utc: {type: string, format: date-time, required: true}
rules:
  - "Chorus thresholds derive from cohort exam observations."
```
- **Recorded:** "**Correlation ledger** | COMP-BMS | Chorus observations and cohort references" (`lenses/logging-spec.md:17`).
- **Enforced via the Chorus flag** — `glossary.md:15`: "**Chorus flag**: Automatic listener for abnormal loss shape. The chorus owns **rate and clustering shape, not amount lost**. DEC-0048." Chorus is a leash-chain rung (`components/book-template.md:30`). Chorus expected-frequency rule = `F_CHORUS`, value `null`, "Certified from cohort exam; exact threshold pending", **GAP-0012** (`registry/variables.md:231-240`, DEC-0048).
- **Gap:** "Cohort correlation cannot be measured → Chorus frequency remains GAP(GAP-0012)" (`components/examination-engine.md:57`; `gap-report.md:22` "Certified leash-event frequency rules"). Cross-book exposure caps = GAP-0008.
- **Summary of computed-vs-enforced:** correlation is **computed** at exam (CT-EXAM-02 observations + expected_loss_shape) and **logged** (correlation ledger); **enforcement** is the chorus flag on abnormal loss *shape/rate*, but the numeric **threshold is not yet certified (GAP-0012)** — so enforcement thresholds are ratified in mechanism only, not in number.

---

## Topic 12 — Money ladder + R (FORM-0004, FORM-0006, variables, seat/offer/take, treasury seed-to-cap+sweep, distinct capital concepts)

**Formula registry (VERBATIM, the money-ladder core)** — `registry/formulas.md:9-55`:
```yaml
  - id: FORM-0001
    name: cap_equity
    expression: "C = cap_multiple * S"
    component: COMP-BOOK-TEMPLATE
    decisions: [DEC-0029, DEC-0038]
    notes: "C is a derived relationship, not an independent registry number; cap is checked at rollover only."
  - id: FORM-0002
    name: runway
    expression: "U = E - K"
    notes: "E is current book equity state."
  - id: FORM-0003
    name: daily_loss_budget
    expression: "D = U / n"
    notes: "Re-derived at rollover and drains intraday."
  - id: FORM-0004
    name: offer_per_seat
    expression: "offer_R_usd = D / (B * b * Lbar)"
    registry_inputs: [scalper_breaker_threshold, scalper_budget_shaping_factor, scalper_mean_loss_r]
    notes: "The book offers; trust-bounded cost-aware Kelly disposes."
  - id: FORM-0005
    name: take_per_seat
    expression: "take_R_usd = min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)"
    notes: "Formula is ratified; the trust-bounded cost-aware Kelly implementation remains a bot/book validation responsibility."
  - id: FORM-0006
    name: r_max_ceiling
    expression: "R_max_usd <= B * b * Lbar"
    notes: "Relationship-stated ceiling is formula-owned; Lbar is measured per bot at exam."
  - id: FORM-0007
    name: viability_floor
    expression: "round_trip_cost_R / expected_edge_R <= v_cost"
```
(FORM-0008..0010 in Topics 13/treasury below.)

**FORM-0004 = `offer_R_usd = D / (B * b * Lbar)`** and **FORM-0006 = `R_max_usd <= B * b * Lbar`** confirmed VERBATIM (`registry/formulas.md:35`, `:50`).

**Variable meanings + units (VERBATIM, `registry/variables.md`):**
- `D` = daily_loss_budget = `U / n` (FORM-0003); `U` = runway = `E - K` (FORM-0002); `E` = current book equity.
- `B` = `scalper_breaker_threshold`, **value 2**, units `consecutive_stopouts` (`:46-54`). "Consecutive stop-outs before bench-to-paper."
- `b` = `scalper_budget_shaping_factor`, **value 2**, units `ratio` (`:55-63`). Operator-countersigned coefficient used by offer-per-seat.
- `Lbar` = `scalper_mean_loss_r`, value `measured_per_bot_at_exam`, units `R`, `kind: measured`, `reference_expectation: 0.35`, `configurable: false` (`:64-74`). "0.35R is a reference expectation only and never an inherited bot default."
- `S` = `scalper_seed_capital` = **500 USD**, constraint `S > K` (`:9-18`); `K` = `scalper_kill_line` = **200 USD**, "Fixed within the cycle" (`:19-27`); `cap_multiple` = `scalper_cap_multiplier` = **2.5** (`:28-36`); `n` = `scalper_runway_divisor` = **5**, "Floor-trader discipline number" (`:37-45`); `v_cost` = `viability_cost_fraction_max` = **0.10** (`:75-83`).

**Seat / offer / take mechanics (VERBATIM):** "The book offers; trust-bounded cost-aware Kelly disposes" (FORM-0004 note); take = `min(book offer, trust-bounded cost-aware Kelly)` (FORM-0005). Book-template config: "Take per seat | `formula:FORM-0005 take_per_seat` | Minimum of book offer and trust-bounded cost-aware Kelly." (`components/book-template.md:55`). Scalper "offer[s] risk seats" and has a "live seat" (`components/scalper-book.md:11`, mermaid `:39`).

**Treasury seed-to-cap + sweep (VERBATIM)** — `components/treasury-desk.md:7`: "Treasury owns the virtual capital ledger and the book-to-treasury boundary. **Only sweep, refund, and re-seed cross that boundary**. DEC-0038." `:24`: "The cycle is **seed to cap**. The book **compounds within a cycle and ratchets between cycles**. DEC-0006." `:26`: "**Sweep is checked at rollover only**. If cap is hit intraday, the book completes the day and sweep uses rollover equity. DEC-0038." Sweep def (`glossary.md:33`): "Rollover-only treasury event that moves equity above seed into treasury accounting and **resets book equity to seed**. DEC-0038."
- Treasury records: "seed, equity, kill line, cap, cycle id, cycle state, sweep, refund, re-seed, and reconciliation verdicts" (`components/treasury-desk.md:11`).
- FORM-0008 refund_reserve (VERBATIM, `registry/formulas.md:64-72`): `reserve_usd ~= rho * N_cycles_month * S`, GAP-0007 (exact rho estimator open); `rho`/`N_cycles_month` values `null` (`registry/variables.md:84-103`).

**Distinct capital concepts (from Treasury/registry):** **Seed S** (cycle start capital, 500), **Kill line K** (floor, 200, S>K), **Equity E** (current book state), **Runway U = E−K** (loss capacity), **Cap C = 2.5·S** (sweep trigger ceiling, rollover-checked), **Daily loss budget D = U/n**, **Refund reserve** (treasury buffer), **virtual/broker equity** (reconciliation, CT-BMS-03). Money resets between cycles; **knowledge persists** (L5, `system-constitution.md:19`; SCN-0002 `:31`).

**R unit:** R is the risk unit (`requested_r units: R` CT-BOOK-01; `EV_OOS_MIN` etc. in R). "Never redistribute unclaimed budget" (L4 `:17`, DEC-0005).

---

## Topic 13 — Stop-out (definition; breakeven-exit ambiguity; consecutive counter B=2)

- **Consecutive-stop-out counter `B=2`** — CONFIRMED VERBATIM: `scalper_breaker_threshold` symbol `B`, `value: 2`, units `consecutive_stopouts`, "Consecutive stop-outs before bench-to-paper" (`registry/variables.md:46-54`). After B consecutive stop-outs the bot benches to paper for the day, auto-resets next open (DEC-0032; `components/paper-mode-system.md:24`; `components/scalper-book.md:26`,`:56`).
- **B also feeds sizing:** appears in FORM-0004 offer and FORM-0006 R_max as a divisor/ceiling factor (`registry/formulas.md:38`,`:53`).
- **Breakeven / break-even probability** — FORM-0010 (VERBATIM, `registry/formulas.md:80-86`): `break_even_probability: p > (L + c) / (W + L)`; note "Cost discipline is structural for scalping." FORM-0009 expectancy: `EV = p * W - (1 - p) * L - c` (`:73-79`), note "Never compute EV from winning-trade anatomy alone." These are **exam expectancy** formulas.
- **NOT found:** a precise definition of "stop-out" as an event, and the **"breakeven-exit ambiguity"** (whether a breakeven exit counts as a stop-out toward B) is **not addressed** — the corpus never states whether a scratch/breakeven exit increments the consecutive-stop-out counter. (See Not-found.)

---

## Topic 14 — Alpha-decay evidence classes / 'the Book sets the bar' / qualification metrics / exam certificates / certified footprint

- **Exam gate (VERBATIM)** — `components/examination-engine.md:25`: "The exam gates on two conditions: **the edge is real after costs, and the candidate is not fiction**. DEC-0036. Everything else becomes measured input for the book wallet, leash, and chorus." Bot "is validated against the book contract it applies to join" (`:7`, DEC-0055) — i.e. the **Book sets the bar**.
- **CT-EXAM-01 Exam Certificate (VERBATIM, the certified footprint)** — `contracts/ct-exam-01-exam-certificate.md:7-23`:
```yaml
id: CT-EXAM-01
title: Exam Certificate
status: reviewed
decisions: [DEC-0011, DEC-0036, DEC-0055]
fields:
  bot_id: {type: string, required: true}
  book_profile: {type: string, required: true}
  labeler_versions: {type: object, required: true}
  ev_by_regime: {type: object, required: true}
  mean_loss_r: {type: number, required: true}
  fire_rate_band: {type: object, required: true}
  breaker_expectation: {type: object, required: true}
  cost_ratio: {type: number, required: true}
rules:
  - "Certificate is invalid if live labelers differ from exam labelers."
```
- **Footprint (VERBATIM)** — `glossary.md:23`: "**Footprint**: A book's measured behavior envelope. The footprint is **measured in exam and live journals, not accepted from bot self-description**. DEC-0035." Footprint is door #1 of the seven doors.
- **Qualification metrics (registry, VERBATIM values, `registry/variables.md:123-185`):** `walk_forward_in_sample_months` 6; `walk_forward_out_of_sample_months` 1; `min_oos_trades_per_window` 200; `oos_expectancy_floor_r` 0.15 R (after modeled costs); `monte_carlo_shuffle_count` 1000; `pbo_pass_threshold` 0.25 ("Below this value passes"); `pbo_dead_threshold` 0.50 ("Above this value is dead"). Exam measures: regime-conditional EV, mean loss, fire-rate bands, cohort correlation (`components/examination-engine.md:11`).
- **Exam-live parity law** — L10 (`system-constitution.md:29`): "Exam labeler versions and live labeler versions must match. DEC-0011." Mismatch invalidates the certificate until re-exam (`components/examination-engine.md:55`).
- **NOT found by name:** "alpha-decay evidence classes" as a discrete taxonomy, and "exam certificates" as literally certifying against ongoing alpha-decay. The nearest concepts are PBO (probability of backtest overfitting) thresholds, walk-forward OOS windows, and "sunset review handles pointlessness" (L16, `system-constitution.md:41`, DEC-0017) — decay handling is split between the **leash (damage)** and **sunset review (pointlessness)** but not named "alpha-decay evidence classes." (See Not-found.)

---

## Topic 15 — Book/BMS validation leads (how a NEW Book or BMS proves itself before carrying money)

- **Bot→Book validation** is fully covered by the Examination Engine + CT-EXAM-01/02 (Topic 14): a bot must earn an exam certificate against a specific `book_profile` before live admission; the exam "May never: **authorize live trading**" itself — it only certifies (`components/examination-engine.md:13`). Live authorization flows through the book's seven doors (`components/scalper-book.md` mermaid `:37-41`).
- **How a NEW Book proves itself:** the corpus gives the **template/instance discipline** (ADR-0002) and **paper mode as the diagnostic proving ground** (`components/paper-mode-system.md:7` "Paper mode is diagnostic"), but there is **NO explicit "new-book validation lead / probation" procedure** — no rule that a brand-new Book must run in PAPER for N days before carrying money. Paper↔live promotion semantics are **GAP-0006**. So Book-level validation-before-money is **largely a gap** in this corpus.
- **How a NEW BMS proves itself:** **not addressed** — there is a single BMS; no BMS onboarding/validation concept. (See Not-found.)
- **Financial safety gate that always applies:** unexplained virtual-vs-broker drift is a **technical kill** (CT-BMS-03; L14 `system-constitution.md:37`, DEC-0015), and reconciliation epsilon requires operator review before any non-zero value (`registry/variables.md:104-113`).

---

## Topic 16 — Same-tick priority; no-overnight; hold limits; dead-zone (~45min handover)

- **Ordering that IS specified (two chains):**
  1. **Door pipeline (per-intent order, VERBATIM)** — `components/book-template.md:43`: `intent --> footprint --> viability --> rmax --> budget --> breaker --> exposure --> ksa --> adapter`.
  2. **Leash chain (escalation order, VERBATIM)** — `components/book-template.md:30`: "ambient governor, day closure, bench-to-paper, chorus flag, kill-line stand-down, classed kill switch, and hold-time force-flat. DEC-0037."
- **Graduated-vs-instant law** — L12 (`system-constitution.md:33`): "Graduated policy shrinks before it blocks **unless the event class demands instant action**. DEC-0013." L16: "The leash handles damage; sunset review handles pointlessness. DEC-0017." Intraday protection is **deterministic**, no human in the loop (L3 `:15`; DEC-0022 human chorus loop is dead, `dead-decisions.md:15`).
- **Hold limits:** the only hold construct is the terminal leash rung "**hold-time force-flat**" (`components/book-template.md:30`, DEC-0037) — a max-hold forced flatten. No numeric hold-time value is in the registry.
- **NOT found:** an explicit **same-tick priority resolution** among {protective stops, Book force-flat, kill switch, fast invalidation, discretionary exits} — the corpus gives two *sequential* chains and the graduated-vs-instant law, but no tie-break table for simultaneous same-tick triggers. **No "no-overnight" policy.** **No ~45-minute dead-zone / session-handover no-trade window.** (The only `45` in the corpus is `order_latency_max_ms = 45` ms, `registry/variables.md:204-212` — unrelated.) Session-windows-as-authority is a **dead idea** (DEC-0025, `dead-decisions.md:18`; `components/book-template.md:63`): "the clock alone does not authorize trades … session context may only inform them if ratified." (See Not-found.)

---

## Topic 17 — Multi-currency (numeraire, cross-account aggregation, FX conversion for risk math)

**Almost entirely NOT found in this corpus.**
- Money units are stated in **USD** throughout (seed/kill/cap/amount/equity all `units: USD`), with no account **numeraire** concept and no **FX conversion** rule for risk math. Whole-corpus grep for `numeraire|FX|convert|aggregat` returns nothing relevant.
- The only currency-facing field is `affected_currency` in the **news** directive (CT-BMS-04), used for currency→pair blocking, not for risk-math conversion.
- **Cross-account aggregation:** reconciliation is **per `account_id`** (CT-BMS-03 `:13`); adapter maintains per-command `account_binding` (CT-ADAPTER-01 `:15`). **Cross-book cap aggregation is explicitly GAP-0008**; there is no cross-**account** aggregation rule at all. (See Not-found.)

---

## Contradictions (within this corpus / against the checklist's assumed vocabulary)

1. **Effect vocabulary mismatch (Topic 10).** The checklist names the KSA effect vocabulary as "suspend-new / drain / close_all." This corpus does NOT use "suspend-new" or "drain." Its actual effect verbs are the **adapter command enum** `place_order, cancel_order, close_position, close_all` (`contracts/ct-adapter-01-broker-adapter-command.md:15`) plus prose verbs "block affected pairs," "hard block," "prevents new entries," "blocks broker execution until reconciled." Only `close_all` matches. Flag as vocabulary drift between the risk-sitting checklist and the ratified GitBook baseline.
2. **KSA scope ladder (Topic 10).** Checklist assumes scopes "pair/Book/account/venue/global." Corpus only realizes **pair-array** (`affected_pairs`) + a described **global** state machine. Book/account/venue KSA scoping is not present — potential contradiction with a finer-grained scope model asserted elsewhere.
3. **Book-mode vs seat-state split (Topic 4).** Checklist presumes a "seat-state vs book-mode split." Corpus has an explicit **book-mode** enum (`LIVE/PAPER/BENCHED/STOOD_DOWN`) and a **KSA-level** enum, but **no separate seat-state enum**; "seat" is only a sizing unit. Any external doc asserting a formal seat-state enum would contradict this baseline.
4. **No genuine internal self-contradiction found** among the ratified pages: mode enums, formulas FORM-0004/0006, B=2, seed/kill/cap all agree across contracts, registry, components, and scenarios. Numeric "conversation examples" are explicitly **checksum-only, not authority** (GAP-0011 answered; `gap-report.md:30`; `scenarios/scn-0001-money-ladder.md:32`).

---

## Not-found list (checklist topics with NO / only-partial evidence in THIS corpus)

- **T1:** No "CT-BOOK-03" and no standalone "book object" field schema (only CT-BOOK-01 intent + CT-BOOK-02 mode). Book "Section 6" workspace = GAP-0001.
- **T5:** No book-type versioning rule; **no "scalping-book-v2 = NEW Book, never inherits v1 ledger"** statement. Only footprint/snapshot/labeler versioning exists.
- **T6:** No dynamic SL/TP mechanics, no "fast invalidation" organ, no position-safety / SL-TP authority split, no rule on who moves stops or when.
- **T7:** No paired-demo bindings, no duplicate-order-prevention rule, no evidence-comparability metric; full paper↔live transition machine = GAP-0006.
- **T8:** No news window length **in minutes** (only UTC start/end), no news-specific severity tiers, no explicit open-position behavior inside a news window, no override mechanism.
- **T9 (SQS):** No `sqs_score` formula, no inputs list, no numeric threshold, no cadence, **no hysteresis**, no explicit "why it existed" rationale. Only the two snapshot fields + "unreachable = hard block."
- **T10:** No formal pair/Book/account/venue/global scope ladder; "suspend-new/drain" effect terms absent; trigger→level target matrix = GAP-0015.
- **T13:** No precise "stop-out" event definition; **breakeven-exit ambiguity unresolved** (whether a breakeven exit counts toward the B=2 counter is not stated).
- **T14:** No named "alpha-decay evidence classes" taxonomy; decay handled implicitly via PBO/OOS + leash/sunset split.
- **T15:** No new-**Book** probation procedure before carrying money (paper↔live = GAP-0006); no new-**BMS** validation concept at all.
- **T16:** No same-tick priority tie-break table; **no no-overnight policy**; no numeric hold-time; **no ~45-min dead-zone / session-handover window** (session-windows-as-authority is dead, DEC-0025).
- **T17:** No account numeraire, no FX conversion for risk math, no cross-account aggregation; cross-book cap = GAP-0008.

---

### Appendix — open GAPs relevant to the risk sitting (from `gap-report.md:11-24`)
GAP-0001 Book Section 6 workspace · GAP-0002 notification severity/channels · GAP-0003 data-layer ownership/retention/schema · GAP-0005 broker/cTrader feasibility · GAP-0006 paper/live transition state machine · GAP-0007 refund-reserve rho estimator · GAP-0008 Exposure Desk v2 incl. cross-book cap · GAP-0009 observability substrate · GAP-0010 BMS Section 1-2 assignments · GAP-0012 certified leash-event (chorus) frequency · GAP-0013 QML interface scope · GAP-0015 KSA trigger-to-level target matrix (esp. connectivity & unknown-state).
