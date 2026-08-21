# Rulings binding on the future backtesting / experimentation sitting

Source: `.memlog.md` lines 65–116 (venue sitting + risk sitting), architecture-QMX-2026-08-19.
Every claim below cites the memlog line it rests on. Facts only; where a named item
is not defined inside this line range it is marked **ABSENT (in range)**.

Scope note (memlog:90): after the venue increment, "scope now GAP-0001..0038 with
0016/0017 deferred. Sitting remainder: risk sitting (GAP-0039..0046), **backtesting
sitting (GAP-0048/0049 + ticket 008)** — then PRD and BMad exit." The backtesting
sitting is the next design sitting after risk; the ADs below are its inherited invariants.

---

## AD-number mapping caveat

The risk sitting's ADs are named in this range only where a ruling references them:
**AD-33** (Book exit policy / exit door), **AD-34** (breakeven ratchet / protection
amendment), **AD-36 & AD-37** ("assign who may act and in what order", memlog:114),
**AD-38** (protection windows / control-window contract CT-31, memlog:113), **AD-40**
(pre-declared full-loss price + B-coupling split, memlog:115–116), **AD-41** (bench
counter, memlog:115). **AD-29, AD-30, AD-31, AD-32, AD-35, AD-39 are ABSENT (in range)**
— their exact numbers are assigned in the post-line-116 spine re-distill, not in this
window. The one-liners below are organized by the binding SUBSTANCE the task named;
AD numbers are attached only where the memlog itself attaches them.

---

## 1. Book / BMS / binding chain (GAP-0039; DEC-0095/DEC-0115)

- **Binding chain = bot -> Book -> BMS -> account**; the **BMS, not the Book, connects
  to the account** (operator correction, memlog:100; corpus-verified verbatim in all
  three legacy layers, constitution L1: "Bots trade; books control bots; BMS accounts
  for and constrains books; nothing above a bot touches the market. Hierarchy: bot ->
  book -> BMS -> operator", memlog:101, cite `Documents/QMX wiki system/invariants.md:19`).
- **BMS = versioned RULEBOOK** (protection posture + risk transitions, "more risk
  managing than position sizing"), never a machine above Books; GitBook/self-doc BMS =
  DEFAULT v1 template (memlog:92). Refined: BMS is the **account-facing supervising
  layer** (CT-BMS-03 reconciliation is per account_id) (memlog:101).
- **Cardinalities (final):** bot N–1 Book (DEC-0115 stands); a Book binds **exactly ONE
  BMS at a time** (dated binding, swappable, append-only history); **one BMS version may
  be bound by MANY Books**; **one BMS instance per ACCOUNT** (memlog:92, 101). Crypto/
  prop-firm variants = NEW BMS versions, never simultaneous stacking (memlog:92).
- **Authority split (default v1, verbatim):** "The book owns admission, sizing, doors,
  leash, and profile selection. BMS owns accounting, constraints, journals, KSA policy,
  and reporting" — with the QMF migration caveat that journal/record/session MACHINERY
  is now QMF-side contracts while the BMS keeps the authority (memlog:101).
- **Risk domain = per-account** (Book instance, BMS instance, connection). A cross-broker
  strategy = **several INSTANCES of one Book version/template**; an instance never spans
  venues; cross-broker aggregation = after-the-fact report with stated as-of time
  (memlog:94). Same-tick priority always account-scoped (X-5 resolved, memlog:94/101).
- **Defaults + Versions + Copies meta-model** (memlog:93): everything ships as DEFAULTS
  + VERSIONS + COPIES. GitBook shapes = default v1 templates ("the lowest level");
  templates declare configurable vs non-configurable variables; adding a broker account
  => QMX offers a COPY of chosen defaults (Book instance + BMS instance + own connection)
  bound to that account. **VERSION != COPY** (memlog:100): version = template-level change
  (variables changed/added); copy = instantiation of a template/version onto an account.
- Book/BMS templates are **structured config artifacts (JSON-Schema-class)**; every
  variable declared **UI-EDITABLE vs UNEDITABLE in the template itself**; UI edits mint
  new versions, never mutate (memlog:107).

## 2. Kill switch seams (GAP; flatten authority)

- **KILL SWITCH = GLOBAL black-swan emergency** — stops ALL trading including paper
  ("flips the entire thing off", "cuts off actual connection"); **sensor-fed (MIS/SQS
  are its inputs)**; human de-escalates (memlog:98).
- **KILL LINE = per-Book capital floor** ("the amount of capital a book touches so that
  it stops trading") — a different thing from the kill switch (memlog:98).
- **Flatten authority assigned** (memlog:98): a **kill-line breach auto-flattens that
  Book's scope** (a 3am breach never waits for the operator); every OTHER money boundary
  (rollover, sweep, re-seed, paper flip) leaves positions alone; the operator may flatten
  anything at any time, authority inalienable.
- **Effect vocabulary (suspend-new / drain / close-all)** lives in the **QMF control
  contract**; **which effect fires per severity = node authority** (memlog:98). Operator's
  "cut the connection" phrasing recorded as evidence, not bound (closing positions
  requires the connection).
- GAP-0015 (trigger->level->effect matrix) stays deliberately empty: the ADs assign who
  may act and in what order, never which level fires what (memlog:114).

## 3. Exit ownership — DEC-0067 resolution (GAP-0040; AD-33 exit door)

- **DEC-0067 RESOLVED FOR V1** (memlog:95): **Book owns exit policy**; bots **PROPOSE
  risk-reducing exits through a versioned Book door** (fast invalidation preserved); the
  **Book executes or refuses with recorded reason**.
- RIDER: later Book versions may delegate specific exit organs to specific bot families —
  the door grammar is versioned, delegation = a version change not a rule break ("for now
  option one") (memlog:95).
- Exit door atom = **QML donor `ExitLogicRef {module_id, config}`** carried into the
  Book's exit policy (AD-33); one grammar, per-instance configuration (memlog:109, 115).
- CloseReason taxonomy (SL/TP/trailing/session/hedge/KS/manual/broker) = the multiple-
  exit-methods mechanism; reused for the typed why-it-closed label (memlog:109, 104).

## 4. Stop-out definition (GAP-0045; AD-41 bench counter)

- **Stop-out = exit at ~full planned loss (-1R)** ("we only count losses at negative 1R");
  **breakeven exits do NOT count toward the bench** ("break-even is okay") (memlog:99).
- The **bench counter counts STOP-OUTS**; **threshold is PER-BOT** (2 = "perfect" for a
  scalper) and **emphatically CONFIGURABLE** (strategy-family-dependent: scalper vs holders
  vs crypto; bots may use multiple exit methods) — **typed + versioned + configurable,
  never hardcoded** (memlog:99).
- **Breakeven exits recorded as their own metric** (clustering watch; reversible later
  from data) (memlog:99). This closes the dig's Q4 and the GAP-0045 stop-out half.

## 5. R and FORM-0006 replacement (GAP-0044 dimensional mandate; AD-40)

- **R definition (only complete one in corpus, frozen):** "1R price distance is entry to
  the original protective stop; 1R in pips is that distance divided by the instrument pip
  size; 1R in cash is the loss if the original stop fills at the admitted quantity; a full
  original-stop loss is -1R; breakeven is 0R" (recovery ADDENDUM:110-116, via memlog:115).
  Current corpus: R = `registry:original_risk_unit`, "exactly one unit of original
  pre-trade risk; not profit, equity, or post-trade return" (`docs/registry/variables.yaml:427-436`,
  DEC-0076, memlog:115).
- **R is FROZEN AT ADMISSION** — never re-based by a stop move, a protection amendment
  (breakeven ratchet included), or an intraday budget re-derivation; this keeps -1R
  meaning a full loss and keeps the bench counter calibrated (memlog:115).
- **B-coupling split (the defect that motivated GAP-0044):** one symbol B did two unrelated
  jobs — a **count** (consecutive stop-outs before bench) and a **depth in R** (divisor in
  FORM-0004, ceiling factor in FORM-0006) (memlog:116).
  - **RESOLUTION = TWO typed variables, different unit-kinds:**
    `bench_consecutive_loss_threshold` **[count]** on the leash (per-bot, configurable,
    UI-editable; recorded 2 is evidence, never ratified) and `seat_loss_run_allowance`
    **[r_multiple]** on the money rules (memlog:116).
  - A Book MAY declare the second derived from the first
    (`threshold x safety_multiple x measured_mean_loss`) as **DECLARED FINGERPRINTED
    DATA** visible in the charter and every consuming artifact — never a hardcoded
    identity (memlog:116).
- **FORM-0004 SUPERSEDED** (dimensionally coherent but MIS-NAMED: computes USD-per-R rate,
  not an amount) (memlog:116).
- **FORM-0006 DEAD BY NAME** (DEC-0077; USD <= R is a category error), re-expressed in
  pure R-space as `seat_r_ceiling <= seat_loss_run_allowance`; **FORM-0006 is RETAINED as
  the dimensional suite's PERMANENT NEGATIVE TEST** — "a dead formula that can still be
  typed is a dead formula that comes back" (memlog:116).
- Standing mandate: **every replacement formula must define typed unit-carrying variables**;
  the dimensional checker enforces the split (a count cannot stand where an r_multiple is
  declared) (memlog:91, 116). GAP-0044's dimensional mandate is a STANDING requirement any
  backtesting formula inherits.

## 6. Value-factor

- **ABSENT (in range) as a standalone ruling.** The only appearance is the dimensionless
  factor **`b`** inside the superseded sizing ladder FORM-0004 (`offer_R_usd = D/(B*b*Lbar)`,
  memlog:116) — `B*b*Lbar` reads dimensionally as [loss events] x [dimensionless] x
  [R per loss event] = [R]. No dedicated value-factor AD is minted within lines 65–116;
  the backtesting sitting should confirm its status against the post-116 distill.

## 7. Window kinds (news / dead zone / handover — AD-38, CT-31)

- **ONE control-window contract (CT-31)** serves news + daily dead zone + session-handover
  buffers; **window kinds a Book enables, addable-never-redefined** (memlog:113, AD-38).
- **DEAD ZONE = BOTH window kinds** (operator round 5, memlog:110): the **daily no-session
  band** (~3h per QMX-discussion Flow 9) AND **per-handover buffers** (~45min, operator's
  newer idea) — each a configurable window kind a Book enables; **calendar-dependent,
  absent for 24/7 crypto** (memlog:110, 113).
- **Window carried as TWO INSTANTS, not a minutes offset** (so a stored window cannot
  re-mean under a later policy) (memlog:113).
- **Widen-never-shrink, forward-only**: session scoping/revisions may widen a block but
  never narrow it; decisions under an older revision stand and are tagged (memlog:113).
- **News blackout stops ALL trading on that instrument — live AND paper, no exceptions**
  ("I can't risk it. For now", memlog:97; corpus-confirmed CT-BMS-04 ":36", memlog:113).
  Multi-pair bots blocked **per instrument only** (a multi-pair bot keeps trading its
  unblocked instruments) (memlog:97, 113).
- **Currency->instrument mapping re-mechanised:** legacy symbol-parsing rule dies (AD-9
  bans symbol parsing); survives via **declared dated per-instrument currency-exposure
  records** (AD-9 metadata, operator-correctable); missing record => treated as affected
  and blocked + journaled data quality (memlog:113).
- **All numbers configurable UI-editable defaults with NO spine value**: the +/-15min news
  buffer is WITHDRAWN (DEC-0072, `docs/registry/variables.yaml:438-460`); ~3h and ~45min
  are recorded evidence, never ratified (memlog:113).
- Dead-zone mechanism: **hard pause on NEW entries only; exits/safety/data never blocked**;
  built from the same window machinery as news, on the Book calendar (memlog:106).

## 8. USD numeraire (operator round 5)

- **NUMERAIRE = USD, system-wide** ("why would I use anything other than USD?") (memlog:111b).
- **Book charter still declares `accounting_currency`** so a later currency is a version
  change; **non-USD bindings refused in V1** (config-level constraint, not ceremony)
  (memlog:111b).

## 9. Pre-declared full-loss price (AD-40)

- **Every position must declare its planned full-loss price BEFORE it opens**; no declared
  price => no `original_risk_distance` => **invalid-input refusal at admission** (memlog:115).
- Grounded: CT-BOOK-01 trade-intent envelope carries `requested_r` "Units: R" as a REQUIRED
  field (`Documents/QMX wiki contracts/ct-book-01-trade-intent-envelope.md:22-32`) — an
  intent cannot be admitted without stating its risk in R (memlog:115).
- **HOW the full-loss price is derived = per-family declaration through the QML donor atom
  `ExitLogicRef = {module_id, config}`** carried into the Book's exit policy (AD-33) — one
  grammar, per-instance config; the DECLARATION ITSELF is universal (memlog:115).
- Whether a stop order actually rests at that price is a separate CT-18 capability + Book
  policy question; the **declaration is required either way, including for Books that park
  no broker-side stop** (memlog:115).
- **Consequence:** a strategy that deliberately runs with no planned loss point cannot
  trade in QMX (memlog:115).

---

## Leads and standing rules the backtesting sitting must honor

### "The Book sets the bar" qualification lead
- Filed as a lead at risk-sitting open (memlog:91). Ratified shape (memlog:108): the
  admission bar = **named unit-carrying requirements**, "**not yet ruled**" is an allowed
  state, and the bar **blocks live money only**.

### Book/BMS validation-mechanism lead
- Filed as a lead ("Books/BMS need own validation mechanism", memlog:91). Ratified
  (memlog:108): **NO performance probation** (redemption loops stay dead) BUT a **TECHNICAL
  SHAKEDOWN precedes live** — (a) **linters** over the template config (completeness, units,
  worked-example arithmetic recompute) plus a **"prediction linter"** = static
  can-this-Book-register-this-bot compatibility check (demo bot registration/execution
  testable in UI); (b) **demo/paper connection-and-execution shakedown** ("paper trade to
  see if the Book can actually connect and work properly"); (c) **one operator signature on
  one assembled page**. Trading-node treatment of new-Book/BMS validation ("validation like
  a bot — similar but not so similar") exists in archive/recovery + Documents/QMX; distill
  cites it.

### Paper accounts = world live (AD-12)
- Lead at sitting open: **paper accounts world = live (AD-12)** (memlog:91).
- **Paper package ratified with riders** (memlog:104): DEC-0070 confirmed ("by default the
  paper is meant to be the Book"); **paper = standing evidence state**; frozen paper money
  never Treasury / never buys seats; **BENCHED = bot-seat word only**, Book modes are
  **LIVE|PAPER**; **decay comparisons in R with refusal on cohort mismatch**; return-to-live
  automatic only on clocked causes, operator signature for anything touching real money;
  typed why-it-closed label on every close; whole trade credited to opening bot; broker-side
  protective stop attached wherever CT-18 declares support.
  - RIDERS: (1) **multiple demo accounts exist**; the single-active-paper-target rule is
    **PER LIVE BINDING** (duplicate-order prevention), not a global one-demo-account claim;
    (2) **paper starting balance = Book/family-scoped CONFIGURABLE default (UI)**, resettable
    by dated operator action, **sized for data-collection realism** ("the amount should be
    correlating to this goal"); (3) demo+live = two connections, paired demo bindings
    (AD-27/28) (memlog:104).
- **Two-status split** (memlog:107): Book live|paper; bot seat active|benched (benched
  collectible as data); status = **read-time fold over journals**.
- **Journals = the "logbook"** (memlog:107): Book journal, BMS journal, per-bot journals
  are the data-collection points (defined in Documents/QMX); distill binds **per-entity
  journal streams with paper AND live worlds SEPARATED** onto AD-21 machinery.
- **Suppressed-decision journaling** (memlog:97): a news/blocked bot's would-have-been
  actions are still recorded — "**recording is not trading**", decay sensing keeps its
  data points. (Directly relevant to shadow/simulated evaluation.)

### GAP-0016 / GAP-0017 deferral terms
- **Deferred** — post-venue scope is "GAP-0001..0038 **with 0016/0017 deferred**"
  (memlog:90). One binding consequence recorded: the ordering/emission invariant with the
  **in-component look-ahead assertion binds NOW, independent of the deferred GAP-0016**
  (memlog:68); the **lifecycle-fold half of the annotation deferral was pulled forward**
  (memlog:68). The full substantive content of GAP-0016/0017 is **ABSENT (in range)** —
  only their deferred status and these carve-outs appear.

### Corpus-precedence invariant / authority-order ruling (operator round 5, STANDING)
- **AUTHORITY ORDER for risk / position-sizing / live-trading = GitBook + trading-node
  documentation (archive/recovery + Documents/QMX wiki)**; **QMX-discussion's risk/
  position-sizing system was REPLACED and is BARRED as a source there** ("please don't")
  (memlog:111a). QML will change with the system re-basing onto QMF.
- Closure delegation grammar (memlog:111d): "seems already answered in GitBook and the
  trading-node docs — look there; if those don't answer, it's a gap; if the old versions
  also don't, it's genuinely new" — **close from corpus with citations, mark genuinely-new
  pieces explicitly.** (This is the standing method for the backtesting sitting too.)
- Note: QMX-discussion is BARRED **only for risk/position-sizing**; it is CITED for
  non-risk structural definitions (e.g. dead-zone ~3h band, Flow 9), permitted under the
  round-5 authority bar (memlog:113).

### "Configurable" = UI-editable rule (operator round 3, STANDING GLOBAL)
- **Everywhere the operator says "configurable" it means configurable IN THE UI** — every
  configurable variable minted anywhere in QMX must surface as **UI-editable at platform
  level** (SQS thresholds, bench counters, dead-zone widths, paper balances, news buffers,
  everything) (memlog:103). Reinforced at template level: every variable declared
  UI-EDITABLE vs UNEDITABLE in the template itself, "very important" (memlog:107).

### Do-not-re-discuss-node rule (operator round 5)
- Do not re-discuss trading-node internals with the operator; file node material to
  `tracker/trading-node-notes.md` (memlog:111e, 83, 100).

---

## Every mention of backtesting / simulated world / experimentation / QML in range

- **Backtesting sitting scope (memlog:90):** GAP-0048/0049 + ticket 008 — the next design
  sitting after risk, before PRD and BMad exit.
- **Graduation path (memlog:65):** a working **ungoverned / plain-Python experiment**
  graduates into a CT-16 indicator or CT-17 family via the extension shape, **with a
  lineage edge back to the originating experiment** (five-hats R-9). The plain-Python
  escape hatch "is the point" — use normal Python when the framework can't articulate a
  concept, refactor into the library over time.
- **Extension/graduation mechanics (memlog:67):** generalized in AD-2 (calendar + indicator
  + structure, registration not scanning) + graduation path with lineage to originating
  experiment.
- **Adversarial-review experiments (memlog:66, 67):** "absurd 12-leg experiment", ICT
  "very random confluence", 21/21 concepts pass plain-Python research — review evidence
  that the plain-Python-first path works; not a binding ruling but confirms the escape
  hatch survives governance.
- **Modes declared (memlog:67):** batch-only conformant + heavy-by-definition on live
  path; equality law scoped same-process/same-build; warm-up = integer count in input
  sample unit, mode-identical — relevant to backtest/live determinism.
- **QML direction (memlog:105):** QML (uniform-bot layer, "the original — evolved to go
  beyond the bot") was very likely NOT considered while building QMF core; understand QMF
  vs QML ("very different things") and reconcile; **feeds GAP-0047 (deferred QML consumer)
  and the Bot-schema sitting; nothing in this sitting may foreclose QML's uniformity
  mechanism.**
- **QML dig delivered (memlog:109):** QML = "QML Shared Contract Library" (load-bearing
  uniform-bot layer of the oldest generation); canonical BotSpec formula
  **Bot = Archetype+Features+Filters+Risk+Execution+ExitLogic**; exit method = first-class
  `ExitLogicRef {module_id, config}`; **system-owned SL/TP authority (bot-owned overrides
  rejected)**; CloseReason taxonomy = the multiple-exit-methods mechanism. Disposition:
  role survived (bot-authoring layer), uniform machinery dropped in later generations.
  **Reusable now:** ExitLogicRef atom for the Book exit door; CloseReason taxonomy for the
  typed why-it-closed label; template-grammar vs per-instance-values split. Reconciliation
  = **QML sitting (GAP-0047); nothing in this sitting forecloses it.**
- **Paper as evidence world (memlog:104, 107):** paper = standing evidence state; decay
  comparisons in R with cohort-mismatch refusal; paper AND live worlds separated in
  journals — the simulated-world/backtest evidence discipline.
- **Simulated / paper connection shakedown (memlog:108):** demo/paper connection-and-
  execution shakedown as a validation gate before live money.

The term "backtesting" itself, and any dedicated simulated-world engine design, are
**ABSENT (in range)** beyond the scope pointer at memlog:90 — the substance is deferred to
the backtesting sitting (GAP-0048/0049 + ticket 008). The invariants above are what that
sitting inherits and may not contradict.
