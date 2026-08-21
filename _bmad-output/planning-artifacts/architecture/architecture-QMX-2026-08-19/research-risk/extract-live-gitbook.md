# QMX Live GitBook Extract — Risk Sitting

Source: https://elios-1.gitbook.io/qmx (live GitBook, fetched 2026-08-20 via Firecrawl).
Site map obtained via `firecrawl_map` (65 pages, full enumeration); all pages judged relevant to
the checklist below were scraped in `markdown` / `onlyMainContent` mode so quoted blocks are the
page's own rendered Markdown (YAML/code fences render verbatim; prose paragraphs render as
separate "GitBook Assistant"-suffixed blocks in the raw scrape — that suffix is a UI widget
artifact stripped from quotations below, never part of the source prose).

**Freshness check (vs. 2026-07-18 capture):** `/changelog` has exactly two entries, both dated
**2026-07-08** ("Operator Rulings Applied" and "Initial Provisional Documentation Factory Run").
No entry postdates 2026-07-08. See §"Contradictions / Freshness" below — the live site is
consistent with a 2026-07-18 capture (no revisions logged in the intervening window); nothing
found here should differ from a mid-July capture unless that capture itself predates 2026-07-08.

---

## 1. Book schema (CT-BOOK-01/02/03, versioned book-type schema, seven doors)

Only **CT-BOOK-01** and **CT-BOOK-02** exist in the live contracts index
(https://elios-1.gitbook.io/qmx/contracts). No CT-BOOK-03 page or reference exists anywhere in
the 65-page site map — **not found**.

CT-BOOK-01 Trade Intent Envelope, verbatim
(https://elios-1.gitbook.io/qmx/contracts/ct-book-01-trade-intent-envelope):

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

CT-BOOK-02 Book Mode State, verbatim
(https://elios-1.gitbook.io/qmx/contracts/ct-book-02-book-mode-state):

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

**Seven doors**, verbatim, from Book Template
(https://elios-1.gitbook.io/qmx/components/book-template): "The seven doors are footprint,
viability veto, R_max, daily budget, breaker, exposure ledger, and kill switch. DEC-0035."

**Versioned book-type schema**: the only "version" fields found are `footprint_version` and
`snapshot_version` inside CT-BOOK-01 (per-trade-intent versioning of the footprint/MIS snapshot
used, not a book-type schema version). No standalone "book-type schema version" concept, and no
"scalping-book-v2 is a NEW Book that never inherits v1's ledger" statement exists anywhere on the
live site — **not found** (see Not-found list).

Book template vs. instance split (ADR-0002,
https://elios-1.gitbook.io/qmx/decisions/adr-0002-template-and-instance-split): "The book
template is documented once as sealed Sections 0-5, and the scalper book is documented separately
as the first instance. DEC-0026."

---

## 2. BMS schema (CT-BMS-*, what BMS owns vs. what Book owns)

All five CT-BMS-* contracts exist. Verbatim
(https://elios-1.gitbook.io/qmx/contracts/ct-bms-01-treasury-event …
ct-bms-05-journal-append):

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

**Ownership split**, Book Management System page
(https://elios-1.gitbook.io/qmx/components/book-management-system): "BMS accounts for and
constrains books. It has Treasury, Exposure, Records, and Reporting desks, and it never trades,
sizes, or reaches inside a book. DEC-0045." "May: own virtual ledger state, exposure measurement,
mode registry, append-only journals, reporting metrics, KSA policy, and news block directives."
"May never: trade directly, mutate bot logic, overwrite journals in place, or bypass the veto
ledger."

Constitution Authority Hierarchy (https://elios-1.gitbook.io/qmx/system-constitution): "The bot
owns market-facing entry and exit organs. The book owns admission, sizing, doors, leash, and
profile selection. BMS owns accounting, constraints, journals, KSA policy, and reporting."

"Records is append-only and owns the only journal write path. DEC-0046. Reporting computes from
Records and has zero authority." (book-management-system page). GAP-0008: "Exposure Desk v2
authority remains open, including cross-book cap authority."

---

## 3. Cardinalities (Book↔BMS, bot↔Book, Book↔account/venue)

**Bot↔Book**: `max_concurrent_live_bots` registry entry — verbatim
(https://elios-1.gitbook.io/qmx/registry/variables): `name: max_concurrent_live_bots, symbol:
N_live_max, value: 3, units: bots, type: count, component: COMP-BOOK-SCALPER, decision: DEC-0028,
notes: "ENH-0007 ratified default for the scalper book."` This is direct evidence one Book (the
scalper book) hosts **multiple concurrent bots** (up to 3 live at once). CT-BOOK-01 also carries
one `book_id` + one `bot_id` per trade-intent envelope, i.e., each intent binds exactly one bot to
exactly one book.

**Book↔BMS**: no page states a cardinality (e.g., "one Book may own several BMS" or vice versa).
The dependency graph (https://elios-1.gitbook.io/qmx/architecture/dependency-graph) shows a
single `COMP-BMS` node depended on by `COMP-BOOK-TEMPLATE`, `COMP-KSA`, `COMP-TREASURY`, and
`COMP-NOTIFY` — implying one BMS instance governs the whole system, not per-book BMS instances,
but this is architectural inference, not an explicit cardinality statement — **not found** as an
explicit rule.

**Book↔account/venue**: CT-BMS-03 (Reconciliation Report) has a single `account_id` field per
report; CT-ADAPTER-01 has a single `account_binding` field per command. No statement anywhere
that a Book may bind accounts at multiple venues, or that one account maps to one/many Books —
**not found**.

---

## 4. Book/BMS lifecycle states and modes; seat-state vs. book-mode split

`mode` enum is `[LIVE, PAPER, BENCHED, STOOD_DOWN]`, defined identically in both CT-BOOK-02 (§1
above) and CT-BMS-02 (§2 above). Per CT-BMS-02's rule: **"The BMS mode registry is the
authoritative mode map."** — i.e., the enum's canonical field lives on the Book contract
(CT-BOOK-02) but its authoritative stored state is owned by BMS (CT-BMS-02), confirming the
Book-emits / BMS-owns-of-record split.

**KSA levels are a separate state machine**, not part of Book mode: `GREEN, YELLOW, ORANGE, RED,
BLACK` (registry `ksa_levels`, DEC-0043; https://elios-1.gitbook.io/qmx/registry/variables). This
is the closest documented analogue to a "seat-state vs. book-mode split" — KSA protection level
and Book operating mode are two independent enums governed by two different components (KSA vs.
BMS mode registry).

---

## 5. Book versioning + compatibility

`footprint_version` and `snapshot_version` are the only versioning fields found, both inside
CT-BOOK-01 (per-intent, not per-book-type). Book Template vs. Scalper Book instance split is
covered in §1/ADR-0002. **No statement anywhere on the live site says a new book version (e.g.
"scalping-book-v2") is a wholly new Book that never inherits a prior version's ledger** —
**not found**. The closest adjacent rule is the dead decision "Live restart from kill-line
remnant" (DEC-0023, https://elios-1.gitbook.io/qmx/dead-decisions): "Dead because the remnant is
diagnostic/accounting state. Surviving rule: Kill line means paper mode until re-seed at a cycle
boundary" — this governs cycle-to-cycle continuity within one book, not cross-version book
identity.

---

## 6. Exit ownership; forced exits; fast invalidation; dynamic SL/TP; position-safety authority

Glossary (https://elios-1.gitbook.io/qmx/glossary): **"Bot: The only market-touching actor. A bot
owns entry logic and exit organs while book infrastructure owns admission and sizing. DEC-0002."**

Constitution: "The bot owns market-facing entry and exit organs. The book owns admission, sizing,
doors, leash, and profile selection." (https://elios-1.gitbook.io/qmx/system-constitution)

**Leash chain** (forced-exit escalation path), verbatim, Book Template
(https://elios-1.gitbook.io/qmx/components/book-template): **"The leash chain escalates through
ambient governor, day closure, bench-to-paper, chorus flag, kill-line stand-down, classed kill
switch, and hold-time force-flat. DEC-0037."** — "hold-time force-flat" is the only
hold-limit-triggered forced-exit mechanism named; no duration value is attached to it anywhere in
the registry — **not found** as a numeric hold limit.

Broker Adapter command vocabulary (CT-ADAPTER-01, verbatim,
https://elios-1.gitbook.io/qmx/contracts/ct-adapter-01-broker-adapter-command):

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

"Bots never see broker platforms, and KSA reaches bots only through effects. DEC-0008."
(https://elios-1.gitbook.io/qmx/components/broker-adapter) — i.e. forced exits are effected as
adapter commands (`close_position`/`close_all`), never as direct bot instruction.

**Dynamic SL/TP — who moves stops, when**: not documented anywhere on the live site — **not
found**. No field, contract, or prose describes stop/target adjustment mechanics beyond the bot
owning "exit organs" in the abstract.

---

## 7. Paper mode: bench-to-paper, paired demo bindings, duplicate-order prevention, live↔paper, evidence comparability

Paper Mode System (https://elios-1.gitbook.io/qmx/components/paper-mode-system): **"Paper mode is
diagnostic. It freezes the counterfactual balance at flip and preserves evidence after a breaker,
kill-line stand-down, or demotion. DEC-0014."**

"After `registry:scalper_breaker_threshold` consecutive stop-outs, the affected bot benches to
paper for the rest of the day and auto-resets at next open. DEC-0032." **GAP-0006: "the complete
paper/live transition state machine remains open"** — explicitly, non-breaker promotion,
discretionary promotion, freeze, demotion, and general return-to-live semantics are gap-bound, not
ratified.

CT-PAPER-01 Paper Mode Transition, verbatim
(https://elios-1.gitbook.io/qmx/contracts/ct-paper-01-paper-mode-transition):

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

**Evidence comparability**: SCN-0003 (https://elios-1.gitbook.io/qmx/scenarios/scn-0003-news-block)
proves news blocking applies identically to live and paper: "Both entries are refused... no paper
data is collected under a known invalid news window. DEC-0010." Fixture assertion: "live and paper
produce the same refusal class for the same affected pair and window."

**"Paired demo bindings" and "duplicate-order prevention"**: neither term nor an equivalent
mechanism appears anywhere on the live site — **not found**.

Dead decision context (https://elios-1.gitbook.io/qmx/dead-decisions): "Live restart from
kill-line remnant... dead because the remnant is diagnostic/accounting state. Surviving rule: Kill
line means paper mode until re-seed at a cycle boundary. DEC-0023."

---

## 8. News protection

CT-BMS-04 fields (§2 above) define `affected_currency`, `affected_pairs` (array),
`window_start_utc`/`window_end_utc`, `reason` — i.e. a currency→instrument (pairs) mapping and a
time window exist structurally, but **no numeric before/after-minute values are defined anywhere
in the registry** (`docs/registry/variables.yaml` has no news-window variable) — **not found** for
exact minute thresholds.

Constitution L9: **"News-affected currency pairs are blocked for all books in live and paper mode.
DEC-0010."** (https://elios-1.gitbook.io/qmx/system-constitution)

KSA trigger classes act as the nearest thing to event-severity tiers, verbatim
(https://elios-1.gitbook.io/qmx/components/kill-switch-authority): **"Trigger classes are
scheduled news, black swan, connectivity, and unknown state. DEC-0044."** (CT-KSA-01 enum:
`[scheduled_news, black_swan, connectivity, unknown_state]`) — these are *trigger classes*, not a
numeric severity-tier scale; no tiering beyond the KSA GREEN/YELLOW/ORANGE/RED/BLACK level enum is
documented, and no explicit news→KSA-level mapping exists (GAP-0015, "KSA trigger-to-level target
matrix... remains open," https://elios-1.gitbook.io/qmx/gap-report).

**Open-position behavior during news** (does an existing position get force-closed, or only new
entries blocked?): SCN-0003 only tests refusal of *new* candidate entries during the blocked
window; no statement addresses open positions held into a news window — **not found**.
**Overrides**: not found anywhere.

---

## 9. SQS / spread-quality sensing

CT-MIS-01 fields include `spread_state: {type: enum, values: [normal, elevated, extreme]}`,
`sqs_score: {type: number}`, `sqs_hard_block: {type: boolean}` (verbatim below).

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

MIS behavior (https://elios-1.gitbook.io/qmx/components/market-intelligence-service): **"Failure
is conservative: failed labelers mark degraded fields, SQS unreachable creates a hard door block,
and dead feed state prevents new entries. DEC-0042."** MIS failure mode table: "SQS unreachable →
Door performs hard block. DEC-0042."

**No formula, input list, threshold value, cadence, or hysteresis logic for `sqs_score` is
published anywhere** on the live site (not in `registry/variables.yaml`, not in
`registry/formulas.yaml`) — **not found**. WHY it existed is implicit only: it is an
information-only MIS field consumed by a door as a hard-block gate when unreachable, i.e. a
liquidity/spread-quality circuit-breaker input, but no rationale prose is given beyond that.

---

## 10. Kill switch / KSA

CT-KSA-01, verbatim (https://elios-1.gitbook.io/qmx/contracts/ct-ksa-01-kill-switch-state-event):

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

Authority model (https://elios-1.gitbook.io/qmx/components/kill-switch-authority): **"KSA is the
global protection state machine. BMS owns policy, the trading node enforces effects through the
adapter, and bots never see KSA directly. DEC-0008."** "May never: de-escalate automatically, ask
bots to interpret KSA state, or revive the dead half-size-through-bad-conditions level. DEC-0009,
DEC-0019."

Constitution L8: **"Automated KSA transitions escalate only; de-escalation requires A1 human
authority. DEC-0009."** Glossary: "A1 gate: Human resurrection authority. A1 governs
return-to-live and never performs automatic protection. DEC-0004."

**Scope model**: CT-KSA-01 carries only `affected_pairs` (array) as a scoping field — pair-level
scoping is explicit; a global (system-wide) scope is implied when the field targets all pairs, but
**no Book-level, account-level, or venue-level KSA scope field exists** — **not found** for
Book/account/venue-scoped kill authority.

**Effect vocabulary**: the checklist's expected terms "suspend-new / drain / close_all" are only
partially matched. CT-ADAPTER-01's `command_type` enum is `[place_order, cancel_order,
close_position, close_all]` (§6 above) — `close_all` matches exactly; `close_position` is the
partial-drain analogue; nothing named "suspend-new" or "drain" appears verbatim anywhere on the
live site. Flagged in Contradictions below.

**Adapter interaction**: KSA page interface table: `KSA event | out | CT-KSA-01 | COMP-ADAPTER`.
Dependency graph (https://elios-1.gitbook.io/qmx/architecture/dependency-graph): `COMP-KSA
depends_on: [COMP-MIS-LIVE, COMP-BMS, COMP-ADAPTER]`. Broker Adapter page confirms: "Unknown
startup state emits the `unknown_state` trigger class and blocks broker execution until
reconciled. DEC-0044. The target KSA level for that trigger class remains GAP(GAP-0015)."

---

## 11. Correlation ledger / correlation rules

CT-EXAM-02 Cohort Correlation Certificate, verbatim
(https://elios-1.gitbook.io/qmx/contracts/ct-exam-02-cohort-correlation-certificate):

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

**What is computed**: `correlation_observations` and `expected_loss_shape`, produced by the
Examination Engine at cohort-certification time (component `COMP-EXAM`,
https://elios-1.gitbook.io/qmx/architecture/dependency-graph). **What is enforced**: the "chorus
flag" — glossary, verbatim: **"Chorus flag: Automatic listener for abnormal loss shape. The chorus
owns rate and clustering shape, not amount lost. DEC-0048."**
(https://elios-1.gitbook.io/qmx/glossary) — enforcement acts on shape/clustering/rate of losses,
not loss magnitude. The chorus flag sits in the leash escalation chain (DEC-0037, §6 above). Its
exact firing threshold is unratified: registry `chorus_expected_frequency_rule` (symbol
`F_CHORUS`) has `value: null`, `gap: GAP-0012`, note: "Certified from cohort exam; exact threshold
pending." (https://elios-1.gitbook.io/qmx/registry/variables) No correlation *formula* is
published anywhere — **not found** for a computation method.

---

## 12. Money ladder + R

FORM-0004 and FORM-0006, verbatim (https://elios-1.gitbook.io/qmx/registry/formulas):

```yaml
- id: FORM-0004
  name: offer_per_seat
  expression: "offer_R_usd = D / (B * b * Lbar)"
  component: COMP-BOOK-TEMPLATE
  decisions: [DEC-0030]
  registry_inputs: [scalper_breaker_threshold, scalper_budget_shaping_factor, scalper_mean_loss_r]
  configurable_coefficients: [scalper_breaker_threshold, scalper_budget_shaping_factor]
  notes: "The book offers; trust-bounded cost-aware Kelly disposes."
- id: FORM-0006
  name: r_max_ceiling
  expression: "R_max_usd <= B * b * Lbar"
  component: COMP-BOOK-TEMPLATE
  decisions: [DEC-0030, DEC-0035]
  registry_inputs: [scalper_breaker_threshold, scalper_budget_shaping_factor, scalper_mean_loss_r]
  configurable_coefficients: [scalper_breaker_threshold, scalper_budget_shaping_factor]
  notes: "Relationship-stated ceiling is formula-owned; Lbar is measured per bot at exam."
```

Both formulas confirmed **verbatim matching** the checklist's expected forms: `offer_R_usd =
D/(B*b*Lbar)` and `R_max_usd <= B*b*Lbar`.

Full formula registry (all 10 entries), verbatim
(https://elios-1.gitbook.io/qmx/registry/formulas):

```yaml
formulas:
  - id: FORM-0001
    name: cap_equity
    expression: "C = cap_multiple * S"
    registry_inputs: [scalper_seed_capital, scalper_cap_multiplier]
    notes: "C is a derived relationship, not an independent registry number; cap is checked at rollover only."
  - id: FORM-0002
    name: runway
    expression: "U = E - K"
    notes: "E is current book equity state."
  - id: FORM-0003
    name: daily_loss_budget
    expression: "D = U / n"
    notes: "Re-derived at rollover and drains intraday."
  - id: FORM-0004   # offer_per_seat, see above
  - id: FORM-0005
    name: take_per_seat
    expression: "take_R_usd = min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)"
    notes: "Formula is ratified; the trust-bounded cost-aware Kelly implementation remains a bot/book validation responsibility."
  - id: FORM-0006   # r_max_ceiling, see above
  - id: FORM-0007
    name: viability_floor
    expression: "round_trip_cost_R / expected_edge_R <= v_cost"
    notes: "Viability is a door formula with configurable cost-fraction coefficient."
  - id: FORM-0008
    name: refund_reserve
    expression: "reserve_usd ~= rho * N_cycles_month * S"
    gap: GAP-0007
    notes: "Interim relationship is countersigned; exact rho estimator remains open."
  - id: FORM-0009
    name: expectancy_in_r
    expression: "EV = p * W - (1 - p) * L - c"
    notes: "Never compute EV from winning-trade anatomy alone."
  - id: FORM-0010
    name: break_even_probability
    expression: "p > (L + c) / (W + L)"
    notes: "Cost discipline is structural for scalping."
```

**Variable meanings and units**, verbatim from `registry/variables.yaml`
(https://elios-1.gitbook.io/qmx/registry/variables):

| Symbol | Name | Value | Units | Notes (verbatim) |
|---|---|---|---|---|
| S | `scalper_seed_capital` | 500 | USD | "Operator-countersigned scalper default."; constraint `S > K` |
| K | `scalper_kill_line` | 200 | USD | "Fixed within the cycle." |
| cap_multiple | `scalper_cap_multiplier` | 2.5 | ratio | "Cap C is derived from S times this multiplier." |
| n | `scalper_runway_divisor` | 5 | count | "Floor-trader discipline number." |
| B | `scalper_breaker_threshold` | 2 | consecutive_stopouts | "Consecutive stop-outs before bench-to-paper." |
| b | `scalper_budget_shaping_factor` | 2 | ratio | "Operator-countersigned default coefficient used by the offer-per-seat formula." |
| Lbar | `scalper_mean_loss_r` | measured_per_bot_at_exam | R | `kind: measured`; `reference_expectation: 0.35`; "0.35R is a reference expectation only and never an inherited bot default." |
| v_cost | `viability_cost_fraction_max` | 0.10 | fraction_of_R | "Smallest seat where round-trip cost does not eat the edge." |
| rho | `refund_reserve_rho` | null | ratio | GAP-0007; "Interim reserve-pricing coefficient; exact estimator remains open." |
| N_cycles_month | `refund_reserve_cycles_per_month` | null | cycles_per_month | GAP-0007 |
| eps_recon | `reconciliation_epsilon` | 0 | USD | `operator_review: true`; "Placeholder... operator review is mandatory before non-zero use." |

**Seat/offer/take mechanics**: "The book offers; trust-bounded cost-aware Kelly disposes."
(FORM-0004 notes). Final take = `min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)`
(FORM-0005) — the Kelly-side implementation itself is explicitly out of scope of the ratified
formula ("remains a bot/book validation responsibility").

**Treasury seed-to-cap + sweep**, verbatim (https://elios-1.gitbook.io/qmx/components/treasury-desk):
"Treasury owns the virtual capital ledger and the book-to-treasury boundary. Only sweep, refund,
and re-seed cross that boundary. DEC-0038." "The cycle is seed to cap. The book compounds within a
cycle and ratchets between cycles. DEC-0006." "Sweep is checked at rollover only. If cap is hit
intraday, the book completes the day and sweep uses rollover equity. DEC-0038." Confirmed by
SCN-0002 (https://elios-1.gitbook.io/qmx/scenarios/scn-0002-rollover-sweep): "This scenario proves
that cap contact does not re-anchor the book intraday... No intraday sweep occurs. At rollover,
Treasury records a sweep event for equity minus seed and resets the book's virtual equity to
seed."

**Distinct capital concepts** confirmed as separate registry/formula entities: Seed (S, input),
Kill line (K, input), Cap (C, FORM-0001 derived), current book Equity (E, runtime state), Runway
(U, FORM-0002 derived), Daily loss budget (D, FORM-0003 derived), Refund reserve (FORM-0008,
GAP-0007 open).

---

## 13. Stop-out; breakeven-exit ambiguity; consecutive-stop-out counter B=2

Confirmed exactly: registry variable, verbatim (https://elios-1.gitbook.io/qmx/registry/variables):
`name: scalper_breaker_threshold, symbol: B, value: 2, units: consecutive_stopouts, ... notes:
"Consecutive stop-outs before bench-to-paper."` — **B = 2 consecutive stop-outs**, matching the
checklist exactly.

Scalper Book failure modes (https://elios-1.gitbook.io/qmx/components/scalper-book): "Kill line is
crossed → Flip to paper until cycle-boundary re-seed; live remnant restart is dead. DEC-0023."
Paper Mode System: "After `registry:scalper_breaker_threshold` consecutive stop-outs, the affected
bot benches to paper for the rest of the day and auto-resets at next open. DEC-0032."

**No formal definition of "stop-out" itself is given anywhere** (e.g. whether it means an SL fill,
any losing exit, or a specific R-threshold breach), and **no discussion of a breakeven-exit
ambiguity exists on the live site** — both **not found**. This is a genuine documentation gap in
the live corpus, distinct from the counter value itself, which is fully ratified.

---

## 14. Alpha-decay evidence classes; "the Book sets the bar"; qualification metrics; certified footprint

The literal term **"alpha-decay" does not appear anywhere on the live site** — **not found**.
Likewise, the phrase **"the Book sets the bar" does not appear verbatim** — **not found**.

Closest documented analogues:

Glossary, verbatim (https://elios-1.gitbook.io/qmx/glossary): **"Footprint: A book's measured
behavior envelope. The footprint is measured in exam and live journals, not accepted from bot
self-description. DEC-0035."**

CT-EXAM-01 Exam Certificate, verbatim
(https://elios-1.gitbook.io/qmx/contracts/ct-exam-01-exam-certificate):

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

Exam gate, verbatim (https://elios-1.gitbook.io/qmx/components/examination-engine): **"The exam
gates on two conditions: the edge is real after costs, and the candidate is not fiction.
DEC-0036."**

---

## 15. Book/BMS validation leads — how a NEW Book or BMS proves itself before carrying money

The documented validation mechanism is **bot-centric, not Book-centric or BMS-centric**: "The
examination engine certifies whether a bot can join a specific book. A bot is not validated in the
abstract; it is validated against the book contract it applies to join. DEC-0055."
(https://elios-1.gitbook.io/qmx/components/examination-engine)

Exam battery configuration, verbatim (https://elios-1.gitbook.io/qmx/registry/variables):
in-sample window `walk_forward_in_sample_months` = 6 months; out-of-sample window
`walk_forward_out_of_sample_months` = 1 month; `min_oos_trades_per_window` = 200 trades;
`oos_expectancy_floor_r` = 0.15 R ("After modeled costs"); `monte_carlo_shuffle_count` = 1000
shuffles; `pbo_pass_threshold` = 0.25 ("Below this value passes"); `pbo_dead_threshold` = 0.50
("Above this value is dead").

**No mechanism is documented for a Book itself (as opposed to a bot inside it) or for BMS to
"prove itself" before carrying money** — **not found**. The scalper book, as first book-template
instance, is validated only through ADR-0002's template/instance split and its own configuration
(§1, §5), not through an exam-like certification process of its own.

---

## 16. Same-tick priority; no-overnight; hold limits; dead-zone (~45 min session-handover)

**No explicit same-tick conflict-resolution ordering is documented** among protective stops, Book
force-flat, kill switch, fast invalidation, and discretionary exits — **not found**. The closest
available evidence is the **leash escalation chain** (a graduated, not same-tick, ordering),
verbatim (https://elios-1.gitbook.io/qmx/components/book-template): "The leash chain escalates
through ambient governor, day closure, bench-to-paper, chorus flag, kill-line stand-down, classed
kill switch, and hold-time force-flat. DEC-0037." This is an escalation *sequence over time*, not
a same-tick priority arbitration table, so it only partially answers the checklist item.

Constitution L12 offers a general precedence principle, not a same-tick table: **"Graduated policy
shrinks before it blocks unless the event class demands instant action. DEC-0013."**
(https://elios-1.gitbook.io/qmx/system-constitution)

**No-overnight policy**: not found anywhere on the live site.

**Hold limits**: only the unquantified "hold-time force-flat" leash-chain step (above) — no
numeric hold-time ceiling is published.

**Dead-zone (~45 min session-handover no-trade window)**: searched the Ops Runbook
(https://elios-1.gitbook.io/qmx/lenses/ops-runbook), Scalper Book, MIS, and KSA pages —
**no session-handover dead-zone of any duration is documented anywhere on the live site** —
**not found**.

---

## 17. Multi-currency: numeraire, cross-account aggregation, FX conversion for risk math

**Not found.** Every monetary registry variable (`scalper_seed_capital`, `scalper_kill_line`,
`reconciliation_epsilon`, etc.) carries `units: USD` with no alternate-currency variant or
conversion coefficient anywhere in `registry/variables.yaml`
(https://elios-1.gitbook.io/qmx/registry/variables). CT-BMS-03 Reconciliation Report's
`virtual_equity`/`broker_equity` fields are single USD-denominated numbers per `account_id`, with
no FX field. No page states an account numeraire policy, cross-account aggregation rule, or FX
conversion method for risk math. The only "cross-account" adjacent item is **GAP-0008**
("Exposure Desk v2 authority… including cross-book cap authority" —
https://elios-1.gitbook.io/qmx/gap-report), and that is cross-*book*, not cross-*account* or
cross-*currency*, and remains an open gap.

---

## Contradictions / Freshness

- **Changelog dating**: `/changelog` (https://elios-1.gitbook.io/qmx/changelog) lists only two
  entries, both dated 2026-07-08. No entry postdates that date, so the live site as scraped
  (2026-08-20) is unchanged since 2026-07-08 — i.e., it should be **identical** to any capture
  taken on or after 2026-07-08, including a 2026-07-18 capture, unless that capture predates the
  "Operator Rulings Applied" pass. No page-level "last edited" timestamps are exposed by GitBook
  itself beyond this changelog, so finer-grained comparison is not possible from the live site
  alone.
- **KSA effect vocabulary mismatch**: the checklist expects an effect vocabulary of
  "suspend-new/drain/close_all." The live corpus's actual vocabulary (CT-ADAPTER-01
  `command_type`) is `[place_order, cancel_order, close_position, close_all]`. `close_all` matches;
  `close_position` is the closest analogue to "drain"; nothing named "suspend-new" or "drain"
  exists verbatim. This may reflect a naming difference between the pre-2026-08-19 planning
  vocabulary (as reflected in this task's checklist) and the ratified live contract — flagging
  rather than resolving, since only the live site is in scope for this extraction.
- **"CT-BOOK-03" does not exist** on the live site, despite being named as a possible ID pattern
  in the checklist; only CT-BOOK-01 and CT-BOOK-02 are published.
- No other direct contradictions (a claim asserted one way on one page and a different way on
  another) were found; gaps are reported as Not-found rather than Contradicted throughout.

---

## Not-found (no evidence in this corpus)

1. CT-BOOK-03 (or any third Book contract).
2. A "versioned book-type schema" distinct from the per-intent `footprint_version`/
   `snapshot_version` fields; specifically no "scalping-book-v2 = new Book, never inherits v1
   ledger" statement.
3. Explicit cardinality rules for Book↔BMS or Book↔account/venue (bot↔Book cardinality *is*
   evidenced indirectly via `max_concurrent_live_bots`).
4. Dynamic SL/TP mechanics — who moves stops and when; any granular position-safety/SL-TP
   authority beyond "bot owns exit organs."
5. "Paired demo bindings" and "duplicate-order prevention" in paper mode.
6. Numeric news-block window values (minutes before/after); open-position behavior during a news
   window (only new-entry refusal is scenario-tested); any override mechanism for news blocks.
7. SQS formula, inputs, numeric thresholds, cadence, or hysteresis logic.
8. Book-level or account/venue-level KSA scoping (only pair-level `affected_pairs` and implied
   global scope exist).
9. A correlation-ledger computation formula (only the certificate's field shapes are documented).
10. A formal definition of "stop-out" itself, and any discussion of breakeven-exit ambiguity.
11. The term "alpha-decay" and the phrase "the Book sets the bar" (verbatim absent; footprint/exam
    certificate concepts are the closest analogues, see §14).
12. Any Book-level or BMS-level self-validation process (only bot-level exam certification against
    a book contract is documented).
13. A same-tick priority/arbitration table among protective stops, Book force-flat, kill switch,
    fast invalidation, and discretionary exits (only the graduated leash escalation chain exists).
14. A no-overnight policy; a numeric hold-time limit; a session-handover dead-zone of any duration
    (~45 min or otherwise).
15. Any multi-currency numeraire, cross-account aggregation, or FX-conversion-for-risk-math
    content (everything is flat USD; the only cross-scope gap on record is cross-*book*, GAP-0008).
