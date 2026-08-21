# Extract — Local Recovery Corpus (Book / BMS / Risk, GAP-0039..0046)

**Extractor scope:** `C:/Users/Mubarak/Desktop/QMX/archive/recovery/` — `trading-node-delta/` and
`backtesting-engine-retrieval/`. These are *curated recovery syntheses* (authored 2026-08-15..2026-08-17),
not primary sources. Every claim below cites `path:line` in THIS corpus. Where the synthesis attributes a
claim to an underlying layer, that layer + date is recorded in the `[LAYER]` tag. I record precedence; I do
not decide it.

**Layer legend (recorded, not adjudicated):**
- `[OP-2026-08-17]` current operator ruling captured in the recovery addendum (highest).
- `[WIKI-2026-07]` late local wiki / architecture-spine / operator-ratified planning delta.
- `[BMAD-2026-07]` completed BMAD proof story or machine-readable standard (narrow proof authority only).
- `[GITBOOK]` GitBook baseline (live read 2026-08-15; changelog 2026-07-08; immutable capture 2026-07-18).
- `[LEGACY]` surviving `QMX-discussion` legacy mechanics corpus (oldest; body of concepts GitBook renamed).

**Disposition legend used by the corpus** (`trading-node-delta/README.md:19`): `BASELINE` already in GitBook;
`KEEP` later clarification with authority; `RECONFIRM` needs fresh countersign; `REOPEN` contradictory/pending;
`DROP` superseded/out-of-scope.

**File aliases (all absolute):**
- TND-DELTA = `.../trading-node-delta/trading-node-delta.md`
- ADDENDUM = `.../trading-node-delta/recovery-lineage-addendum.md`
- WIKI-INV = `.../trading-node-delta/work/wiki-inventory.md`
- GITBOOK-BASE = `.../trading-node-delta/work/gitbook-baseline.md`
- BMAD-SUP = `.../trading-node-delta/work/bmad-supplement.md`
- TND-HANDOFF = `.../trading-node-delta/restart-handoff.md`
- TND-README = `.../trading-node-delta/README.md`
- TND-LEDGER = `.../trading-node-delta/source-ledger.md`
- BT-RECOVERED = `.../backtesting-engine-retrieval/recovered-backtesting-engine.md`
- BT-WIKI = `.../backtesting-engine-retrieval/work/wiki-design.md`
- BT-STATUS = `.../backtesting-engine-retrieval/work/bmad-status.md`
- BT-IMPL = `.../backtesting-engine-retrieval/work/implementation-evidence.md`
- BT-HANDOFF = `.../backtesting-engine-retrieval/restart-handoff.md`
- BT-LEDGER = `.../backtesting-engine-retrieval/source-ledger.md`

---

## Topic 1 — Book schema (fields, versioned book-type schema, seven doors)

**Seven doors — VERBATIM order** `[GITBOOK]` (GITBOOK-BASE:89, corroborated WIKI-INV:217):
> "Seven admission doors run in order: footprint, viability veto, `R_max`, daily budget, breaker, exposure ledger, KSA."

**Template ordinal Sections 0–5 — VERBATIM** `[WIKI-2026-07]` (TND-DELTA:83; WIKI-INV:116):
> "Sections 0–5 mean charter, footprint, money rules, entrance exam, leash chain, capacity/sweep. There is no current Section 6."

Section 6 = `GAP-0001` workspace, unsettled `[GITBOOK]` (GITBOOK-BASE:94,349; B-03 TND-DELTA:15).
Charter (Section 0) fills, VERBATIM `[GITBOOK]` (GITBOOK-BASE:88): "game played; money shape; customer plus headline metric; death condition."

**Versioned book-type schema** `[WIKI-2026-07]` (TND-DELTA:84):
> "Book types are versioned JSON Schemas; Book instances are schema-validated definitions; behavior-shaping numeric values come from the registry under instance ownership."

**CT-BOOK-03 (versioned book-type contract, Story 5.1, 2026-07-27)** `[BMAD-2026-07]` (TND-DELTA:85; WIKI-INV:118; BMAD-SUP:92):
> "CT-BOOK-03 adds typed filter columns plus a sparse attribute bag; it structurally refuses EAV and carries expression-index promotion metadata for hot attributes." (TND-DELTA:85)
> WIKI-INV:118 adds: "sparse inert/measured/informational attribute bag, expression-index promotion metadata for hot attributes, and structural refusal of EAV." Ratified/active 2026-07-27.

**Contract identifiers (boundary only)** `[GITBOOK]`/`[WIKI-2026-07]` (WIKI-INV:183–185):
- CT-BOOK-01 = Bot→Book intent; `draft`, GitBook-only; "`requested_r` is a proposal, not final sizing" (WIKI-INV:183).
- CT-BOOK-02 = Book→BMS mode; `active`; "Semantics amended for `ADMITTED`/fail-paper; page says amended field schema pending" (WIKI-INV:184).
- CT-BOOK-03 = Book-type definition; `active`; new Story 5.1 contract (WIKI-INV:185).

**NOT quoted verbatim in this corpus:** the exact field lists of CT-BOOK-01/02/03. Only `requested_r`/`requested` (a proposal) is named. Book-type JSON Schema field enumeration is absent here.

---

## Topic 2 — BMS schema (CT-BMS-*), BMS-owns vs Book-owns

**BMS four desks** `[GITBOOK]` (GITBOOK-BASE:194; B-04 TND-DELTA:16): "Four desks: Treasury, Exposure, Records, Reporting."

**BMS ownership — VERBATIM** `[GITBOOK]` (GITBOOK-BASE:195):
> "BMS owns virtual ledger state, exposure measurement, mode registry, append-only journals, reporting metrics, KSA policy, and news directives."
BMS non-authority, VERBATIM (GITBOOK-BASE:193):
> "BMS accounts for and constrains books; it never trades, sizes, mutates bot logic, reaches inside a book, overwrites journals, or bypasses the veto ledger."

Book-owns (contrast) `[GITBOOK]` (GITBOOK-BASE:57): "The book owns admission, sizing, doors, leash, and profile selection."

**CT-BMS contract fields — ALL VERBATIM** `[GITBOOK]` (GITBOOK-BASE:218–222):
```text
CT-BMS-01 Treasury Event:      event_id, book_id, cycle_id, event_type (sweep|refund|re_seed), USD amount, reason, occurred_at_utc. Only these three types may cross the boundary.
CT-BMS-02 Mode Registry Read:  book_id, mode (LIVE|PAPER|BENCHED|STOOD_DOWN), updated_at_utc; declares BMS mode map authoritative.
CT-BMS-03 Reconciliation Report: account_id, virtual_equity, broker_equity, explained_delta, verdict (reconciled|drift|unknown); unexplained drift is a technical kill.
CT-BMS-04 News Block Directive: directive_id, affected_currency, affected_pairs, start/end UTC, reason; applies to live and paper.
CT-BMS-05 Journal Append:      journal, event_id, event_type, free-form payload, refs, occurred_at_utc; corrections append references.
```

**Direction corrections** `[WIKI-2026-07]` (TND-DELTA:110 / K-46B; WIKI-INV:144): CT-BMS-03 direction is Treasury→BMS; "Adapter broker equity is upstream input to Treasury, not a CT-BMS-03 report producer." CT-BMS-01 event direction corrected to Treasury→BMS Records (TND-DELTA:175 / C-23).

**Reconciliation decomposition (Story 5.9)** `[BMAD-2026-07]` (BMAD-SUP:97 / B-06):
> "`explained_delta` becomes exactly four parts: swept-but-unwithdrawn cash, re-seed remnant gaps, PE-7 open-position unrealized-PnL open item, paper-binding exclusion. Residual = broker − virtual − explained. ... any open position forces `unknown`; ... drift journals technical kill, halt=true, auto-resume=false."

**Required journals (owner)** `[GITBOOK]` (GITBOOK-BASE:208–214): Veto ledger (BMS: door, reason, candidate intent, timestamp); KSA audit log (KSA/BMS: trigger class, evidence refs, state level); Trade journal (BMS: fill, snapshot version, book, bot, pair); Book journal (BMS: mode changes, leash events, cycle events); Correlation ledger (BMS: chorus observations and cohort references). NOTE physical writer = Records sole path (Topic 11 / TND-DELTA:50).

---

## Topic 3 — Cardinalities (Book↔BMS, bot↔Book, Book↔account/venue)

- **bot↔Book:** roster model. `roster_capacity = 6` provisional, distinct from `max_concurrent_live_bots = 3` `[WIKI-2026-07]` (TND-DELTA:74 / K-28; WIKI-INV:110). A Book "may cap concurrent live bots and may leave capacity unused rather than assign risk to an unqualified bot" `[OP-2026-08-17]` (ADDENDUM:131). Book "offers risk seats" to bots (GITBOOK-BASE:103).
- **Book↔BMS:** BMS is one system that "accounts for and constrains books" (plural) — one BMS governs many Books `[GITBOOK]` (GITBOOK-BASE:56,193). Unified registration serves the "Book→BMS" direction (TND-DELTA:69). No statement that one Book owns several BMS; the relationship is many-Books-to-one-BMS-system.
- **Book↔account/venue:** "Each live account binding has a paired demo binding" `[WIKI-2026-07]` (TND-DELTA:73 / K-27). V1 is single-venue forex/cTrader (`K-01` TND-DELTA:35; BMAD-SUP:65 "V1 FOREX/CTRADER"). Adapter carries `account_binding` (GITBOOK-BASE:274).

**NOT found:** an explicit ruling that one Book may bind accounts at *several* venues, or a stated Book↔BMS numeric cardinality (1:1 vs 1:N). Multi-venue is explicitly *out of V1* (TND-DELTA:35).

---

## Topic 4 — Lifecycle states / modes; seat-state vs book-mode split

**Book modes vs seat state — VERBATIM** `[WIKI-2026-07]` (TND-DELTA:72 / K-26):
> "Active Book modes are `LIVE` and `PAPER`; `BENCHED` is a roster-seat state; `STOOD_DOWN` is reserved."
WIKI-INV:107: "V1 book modes are `LIVE` and `PAPER`; `BENCHED` is a bot roster-seat state. Wider enum values `BENCHED`/`STOOD_DOWN` are reserved, not active book behavior." Fail-mechanism split, VERBATIM (TND-DELTA:71 / K-25):
> "Book kill-line `LIVE→PAPER` until cycle-boundary re-seed versus bot-seat breaker `LIVE→BENCHED→LIVE` with next-open auto-reset."

**Where the enum lives:** BMS owns the authoritative mode registry/map (GITBOOK-BASE:195,198; CT-BMS-02 mode enum GITBOOK-BASE:219). Story 5.3 restates: "authoritative current map + append-only transitions; CT-BMS-02 exposes only `book_id`, `mode`, `updated_at_utc`; ... reserved BENCHED/STOOD_DOWN refuse with GAP-0015" `[BMAD-2026-07]` (BMAD-SUP:94 / B-03).

**Admission lifecycle** `[WIKI-2026-07]` (TND-DELTA:68 / K-22):
> "Successful human promotion triggers a Trading pull, revalidates at click time, and lands the unit in `ADMITTED`: definition/certificate/placement exist, but there are no intents and no ledger."
Then birth (K-24 TND-DELTA:70): "birth atomically creates the virtual ledger at seed `S`, emits CT-BMS-01 `re_seed` for cycle 1, and makes the unit live-ready rather than pre-live paper." Activation-at-"next rollover" is only *Proposed* (WIKI-INV:105).

**Namespace hazard (REOPEN):** current CT-BOOK-02/CT-BMS-02/CT-PAPER-01 enum tables still mix `BENCHED`/`STOOD_DOWN` into book modes `[contradiction]` (TND-DELTA:154 / C-02; WIKI-INV:290). Four distinct state spaces to separate: Book mode (LIVE/PAPER), bot-seat state (LIVE/BENCHED), supervision stand-down, admission/activation (TND-HANDOFF:41).

**Three "seat" concepts kept separate** `[OP-2026-08-17]` (ADDENDUM:122–131): (1) Roster seat = membership/bot-seat lifecycle in a Book; (2) Risk seat = active Book allocation to which `offer_R_usd`/`take_R_usd` apply; (3) Legacy capital slot = donor object with DPR auction/house-money — `DROP` the slot tables (ADDENDUM:68,129).

---

## Topic 5 — Book versioning + compatibility

- Book types are versioned JSON Schemas; instances schema-validated `[WIKI-2026-07]` (TND-DELTA:84 / K-31).
- Attribute defs immutable/versioned, inert until exact `(attr_id, version)` binding `[WIKI-2026-07]` (TND-DELTA:86 / K-33).
- QML behavior-input change "mints a new spec version" `[WIKI-2026-07]` (TND-DELTA:87 / K-34).
- Certification is against one immutable `bot_spec_version` + one Book profile; "mutation creates a new version" `[BMAD-2026-07]`/`[WIKI-2026-07]` (BT-RECOVERED:116 INV-01, 135; BT-WIKI:125).

**NOT found:** the specific rule that "scalping-book-v2 = a NEW Book that never inherits v1's ledger." No ledger-inheritance-across-book-versions statement exists in this corpus. Closest analogues are the immutable-version-mints-new-version discipline (above) and Treasury "money resets between cycles; knowledge persists" (Topic 12) — neither addresses cross-*version* Book ledger inheritance.

---

## Topic 6 — Exit ownership (bots vs Book; forced exits; dynamic SL/TP; fast invalidation)

**GitBook baseline — VERBATIM** `[GITBOOK]` (GITBOOK-BASE:57):
> "A bot owns market-facing entry/exit organs. The book owns admission, sizing, doors, leash, and profile selection."
Restated (ADDENDUM:150): "GitBook says the bot owns ordinary entry/exit organs while the Book owns admission, sizing, leash, and forced exits."

**Current QMF operator vocabulary (supersedes for authoring boundary)** `[OP-2026-08-17]` (ADDENDUM:153):
> "a confluence contains no exit; exits, sizing, and risk are Book territory."
Reconciliation (ADDENDUM:69, high-level `RULING`, exact contract `DESIGN`): "GitBook's older 'bot owns exit organs' wording is historical tension, not the current QMF authoring rule."
Safe interpretation (ADDENDUM:156–160): "a confluence cannot own quantity, stop authority, or executable exit policy; a Book definition owns the exit/risk/sizing policy applied to a bound bot; the Adapter performs mechanical amendments and closes."

**Dynamic SL/TP placement** `[WIKI-2026-07]` (TND-DELTA:88 / K-35):
> "Dynamic SL/TP belongs to Book money-rule grammar, with BMS configuration authority and Adapter enforcement. A globally uniform stop service is rejected."
WIKI-INV:121: "placement is now book money-rule grammar, with BMS configuration authority and adapter enforcement." Globally-uniform stop service is a `DROP` (TND-DELTA:188 / D-07).

**Who moves stops / when, close priority, position-safety authority = OPEN.** "Stop forms, computation owner, priority, exam pinning, and boundary position fate remain open" (TND-DELTA:88 precision boundary; open frontier #1 TND-DELTA:200). PE-8 = stop-policy version pinning must be pinned into CT-EXAM-01 (BT-RECOVERED:124 INV-09, O-08:368).

**Fast invalidation / forced exits:** named only as one arm of the unresolved same-tick priority set (see Topic 16); no standalone mechanism defined here.

---

## Topic 7 — Paper mode (bench-to-paper, paired demo, duplicate-order prevention, transitions, comparability)

**Trading paper is fail-mechanism-only** `[WIKI-2026-07]` (TND-DELTA:71 / K-25; WIKI-INV:106): two separated paths — kill-line `LIVE→PAPER` (book) and breaker `LIVE→BENCHED→LIVE` (bot seat, next-open auto-reset). Former birth-in-paper/warm-up/exam-to-paper moved to certification (TND-DELTA:67 / K-21; D-06:187).

**Paper freeze semantics — VERBATIM** `[GITBOOK]` (GITBOOK-BASE:243–246):
> "Paper mode freezes the counterfactual balance at transition and preserves sensing/paper execution evidence. Paper balance cannot be hand-adjusted and paper gains are not treasury cash. After the configured count of consecutive stop-outs, the affected bot moves to paper for the rest of the day and automatically resets at next open."

**CT-PAPER-01 fields — VERBATIM (GitBook shell)** `[GITBOOK]` (GITBOOK-BASE:248):
> "`CT-PAPER-01` has `book_id`, optional `bot_id`, `from_mode`, `to_mode`, `frozen_balance`, and `trigger_event_id`."

**CT-PAPER-01 Story 5.8 local standard (richer; NOT global ratification)** `[BMAD-2026-07]` (BMAD-SUP:96 / B-05; R-17 TND-DELTA:146):
> "Local standard adds `frozen_balance_decimal`, `trigger_kind`, paired-demo id, sensing/paper-continuation evidence, and live-drift exclusion. Only `kill_line_stand_down` book LIVE→PAPER and `breaker_bench` bot LIVE→BENCHED are accepted, and only from caller-supplied `transition_ratified:true` evidence."

**Paired demo bindings** `[WIKI-2026-07]` (TND-DELTA:73 / K-27): "Every live account binding has a paired demo binding for fail-mechanism fills, while sensing stays on the pinned canonical live feed." No silent sibling-feed failover (D-10 TND-DELTA:191).

**Duplicate-order prevention / live↔demo ordering** `[BMAD-2026-07]` (BMAD-SUP:89 / E-03):
> "deterministic merge for shared-account order-lifecycle commands solely by `book_sequencer_sequence`; live drift-check exclusion; non-live binding does not create paired-live metadata."
Each Book has a deterministic sequencer for shared live/demo command ordering (TND-DELTA:40 / K-06).

**Evidence comparability:** paper gains never become treasury cash (GITBOOK-BASE:244; constitution GITBOOK-BASE:71 "frozen counterfactual diagnostic, not a cosmetic balance"). News blocks apply to live AND paper (GITBOOK-BASE:68,221). CONTRADICTION on birth→paper ordering: see Topic 12 / C-15.

---

## Topic 8 — News protection

**Ownership + expansion — VERBATIM** `[WIKI-2026-07]` (TND-DELTA:98 / K-40):
> "BMS Exposure, not MIS, owns daily news import/compilation; affected currency expands to all containing pairs; sessions can widen but never narrow; unknown high-impact coverage blocks conservatively."
WIKI-INV:132: "Affected currency expands to every pair containing it; `affected_pairs[]` is a hint; sessions may widen but never narrow. Unknown high-impact coverage blocks conservatively."

**Contract CT-BMS-04 — VERBATIM fields** `[GITBOOK]` (GITBOOK-BASE:221): `directive_id, affected_currency, affected_pairs, start/end UTC, reason; applies to live and paper.`

**Currency→instrument mapping:** "affected currency expands to all containing pairs" (TND-DELTA:98). This IS the mapping rule.

**KSA trigger:** `scheduled_news` is one of four KSA trigger classes; "Scheduled-news directives block affected pairs in both live and paper, and refusals sign the veto ledger" `[GITBOOK]` (GITBOOK-BASE:258,261). Constitution: "News-affected pairs are blocked for every live and paper book" (GITBOOK-BASE:68).

**NOT found (verbatim):** before/after window *minutes*; numeric event-severity tiers (only "unknown high-impact" qualitative); explicit open-position behavior during a news block (folded into PE-7 position fate). News source/transport and exact calendar schema "still need completion" (TND-DELTA:98 precision boundary). Only override rule present = "sessions may widen but never narrow."

---

## Topic 9 — SQS / Spread-Quality Sensing (formula, inputs, thresholds, WHY)

**Meaning — operator ruling (supersedes drift)** `[OP-2026-08-17]` (ADDENDUM:64; TND-DELTA:96 / K-38):
> "SQS means **Spread Quality Sensor**. The legacy mechanism compares instrument-aware historical spread with current live spread, emits score/hard-block evidence, and grants MIS no trade authority."

**Mechanism — VERBATIM** `[OP-2026-08-17]/[LEGACY]` (ADDENDUM:78–84):
> "observe current best bid/ask spread; compare it with a versioned, instrument-aware historical spread baseline; emit a continuous spread-quality score plus hard-block evidence; let MIS carry that evidence without acquiring trade authority; let the Book's relevant door decide the refusal; fail closed when spread quality cannot be established."

**Formula — VERBATIM legacy candidate** `[LEGACY]` (ADDENDUM:88–90):
```text
sqs_score = historical_average_spread / current_live_spread
```
Scale (ADDENDUM:92): "`1.0` means baseline spread, above `1.0` means tighter, and below `1.0` means wider. ... exact conditioning, thresholds, hysteresis, cadence, sentinel encoding, and baseline windows still require explicit ratification."

**Contract exposure** `[GITBOOK]` (GITBOOK-BASE:165): CT-MIS-01 required fields include `sqs_score`, `sqs_hard_block`. "An unreachable SQS causes a hard door block" (GITBOOK-BASE:156). MIS is information-only; the Book door converts to refusal (GITBOOK-BASE:154).

**WHY it existed:** SQS is safety-critical spread gating but was semantically absent in GitBook — a "high-priority recovery delta target because SQS is safety-critical in GitBook but semantically absent" (GITBOOK-BASE:187; T-02:385).

**DO NOT revive as SQS** `[OP-2026-08-17]` (TND-DELTA:190 / D-09; ADDENDUM:95–104; R-08:134): the BMAD `snapshot_quality_score_v1` / `sqs_weighted_component_floor_v1` six-component aggregate (spread, gap, liquidity, feed, sensor freshness, regime quality; integer basis-point qualities/weights) is a *different* aggregate — "reject **snapshot quality score** as the meaning of SQS" (ADDENDUM:100). Reopen separately under a different name if wanted.

---

## Topic 10 — Kill switch / KSA (authority, scopes, escalate-only, effects, adapter)

**Levels + trigger classes — VERBATIM** `[GITBOOK]` (GITBOOK-BASE:257–258):
> "Levels: `GREEN`, `YELLOW`, `ORANGE`, `RED`, `BLACK`. Trigger classes: `scheduled_news`, `black_swan`, `connectivity`, `unknown_state`."

**Authority model** `[GITBOOK]` (GITBOOK-BASE:256,259): "KSA is a global protection state machine; BMS owns policy; adapter enforces effects; bots never interpret KSA. Automated changes escalate only; A1 is required for de-escalation." Constitution (GITBOOK-BASE:66): "Automatic KSA changes may escalate only. De-escalation requires A1 human authority." Unknown startup state blocks broker execution until reconciled (GITBOOK-BASE:260).

**CT-KSA-01 — VERBATIM** `[GITBOOK]` (GITBOOK-BASE:263): "KSA event contains event id, level, trigger class, affected pairs, evidence refs, and effective UTC time."

**Protection funnel + adapter interaction** `[WIKI-2026-07]` (TND-DELTA:99 / K-41; WIKI-INV:133): "MIS senses → standalone KSA decides → Adapter enforces. KSA completion includes connection drain/quiescence." "KSA drains/quiesces account connections before enforcement is complete."

**Effect vocabulary + scopes** `[GITBOOK]` (GITBOOK-BASE:447 / T-17): per-level adapter effects unpublished — candidate vocabulary named as "block new, cancel pending, close positions, close all, pair-scoped versus global." Old `TIGHTEN`/half-size level is forbidden (GITBOOK-BASE:262,370). Scopes present in evidence: **pair** (affected pairs) and **global** (global protection state). Account/venue scope not separately enumerated.

**Legacy donor effect matrix — VERBATIM** `[LEGACY]` (ADDENDUM:142):
> "GREEN normal, YELLOW caution, ORANGE block new entries, RED protective emergency posture, BLACK force-close/shutdown."
Disposition: "Re-anchor carefully. Current escalate-only/A1 de-escalation wins; PE-5 trigger→level/effect mapping still requires ratification."

**Trigger→level matrix = GAP-0015 (OPEN)** (WIKI-INV:134; GITBOOK-BASE:264): "the full trigger→target-level matrix remains GAP-0015, especially connectivity/unknown state." PE-5 = KSA trigger→level/effects incl. fail-closed unknown/unmapped (BT-RECOVERED:388 O-28). BMS↔KSA cyclic-authority edge unresolved (TND-DELTA:170 / C-18; GITBOOK-BASE:409 / T-08).

---

## Topic 11 — Correlation ledger / correlation rules (computed vs enforced)

**Correlation ledger = 1 of 5 Records streams** `[WIKI-2026-07]` (TND-DELTA:50 / K-11): sole-writer streams are `veto_ledger, trade_journal, book_journal, ksa_audit_log, correlation_ledger`. Content (GITBOOK-BASE:214): "chorus observations and cohort references."

**Chorus flag (rate/shape, not amount)** `[GITBOOK]/[LEGACY]` (ADDENDUM:140):
> "GitBook's listener for abnormal loss **rate and clustering shape**, not loss amount. No equivalent complete legacy runtime was found. Preserve concept; GAP-0012 calibration remains open."

**Computed vs enforced split:** CT-EXAM-02 cohort-correlation certificate *records* observations but *enforces* nothing — threshold null. Fields VERBATIM `[GITBOOK]/[BMAD-2026-07]` (BT-RECOVERED:299–307):
```text
CT-EXAM-02: cohort_id, book_id, correlation_observations, expected_loss_shape, certified_at_utc
```
"The correlation method and `F_CHORUS` threshold remain open under GAP-0012. Missing measurement must remain explicit rather than producing an invented threshold" (BT-RECOVERED:308; BT-STATUS:120 "may record observations but must not invent a promotion threshold"). Even a no-gap adapter reconnect emits correlation evidence (TND-DELTA:102 / K-43A).

**So:** correlation is *computed/recorded* (ledger + CT-EXAM-02 observations); the *enforcement* threshold (`F_CHORUS`, chorus gate) was never set — NOT-found as an enforced rule.

---

## Topic 12 — Money ladder + R (FORM-0004, FORM-0006, variables, seat mechanics, treasury)

**Registry variables — ALL VERBATIM** `[GITBOOK]` (GITBOOK-BASE:120–128):
```text
scalper_seed_capital        S            500     USD                         Scalper Book; configurable
scalper_kill_line           K            200     USD; fixed within cycle      Scalper Book; configurable
scalper_cap_multiplier      cap_multiple 2.5     ratio                        Scalper Book; configurable
scalper_runway_divisor      n            5       count                        Scalper Book; configurable
scalper_breaker_threshold   B            2       consecutive stop-outs        Scalper Book; configurable
scalper_budget_shaping_factor b          2       ratio                        Scalper Book; configurable
scalper_mean_loss_r         Lbar         measured per bot at exam   R         Measured, not configurable; 0.35R reference only
viability_cost_fraction_max v_cost       0.10    fraction of R                Book Template; configurable
max_concurrent_live_bots    N_live_max   3       bots                         Scalper Book; configurable
```

**Formulas — ALL VERBATIM** `[GITBOOK]` (GITBOOK-BASE:134–140):
```text
FORM-0001 cap equity        C = cap_multiple * S                                    Derived; checked at rollover only
FORM-0002 runway            U = E - K                                               Current equity minus kill line
FORM-0003 daily loss budget D = U / n                                               Re-derived at rollover, drains intraday
FORM-0004 offer per seat    offer_R_usd = D / (B * b * Lbar)                         Book offer
FORM-0005 take per seat      take_R_usd = min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)   Bot/book validation
FORM-0006 R-max ceiling      R_max_usd <= B * b * Lbar                               Relationship-stated ceiling
FORM-0007 viability floor    round_trip_cost_R / expected_edge_R <= v_cost          Cost-aware viability door
```

**Variable meanings/units** (D = daily loss budget in USD, from FORM-0003; B = breaker threshold in *consecutive stop-outs*; b = budget-shaping factor, ratio; Lbar = mean loss in *R-multiples*, dimensionless) — units per GITBOOK-BASE:120–128 + FORM table.

**R definition — VERBATIM** `[LEGACY]` (ADDENDUM:110–116):
> "`1R` price distance is entry to the original protective stop; `1R` in pips is that distance divided by the instrument pip size; `1R` in cash is the loss if the original stop fills at the admitted quantity; a full original-stop loss is `-1R`; breakeven is `0R`; outcomes may be normalized as R-multiples."
Consequence (ADDENDUM:117): "This makes `Lbar` intelligible as a dimensionless average loss expressed in R-multiples."

**FORM-0006 dimensional defect (do not implement as-is)** `[LEGACY/OP]` (ADDENDUM:119; GITBOOK-BASE:425 / T-12):
> "`FORM-0006` compares `R_max_usd` with `B * b * Lbar`, whose right side has no stated USD dimension. Do not implement or normalize that formula until its intended relationship is explicitly repaired."
FORM-0004's name itself mixes R and USD (GITBOOK-BASE:427). Do not silently normalize (TND-DELTA:172 / C-20).

**Seat / offer / take mechanics** `[OP-2026-08-17]` (ADDENDUM:67,123–127): Risk seat = "the active Book allocation to which `offer_R_usd` and `take_R_usd` apply" — Book *offers* a risk seat, bot/book applies a *bounded take* (`take = min(offer, kelly)`). Open: whether a risk seat has persistent identity or is derived from `(book, bot, cycle, allocation version)` (ADDENDUM:131,195).

**Kelly incomplete by design** `[WIKI-2026-07]` (TND-DELTA:90 / K-37; WIKI-INV:124): "Live Kelly sizing is intentionally incomplete until a trust-bounded, cost-aware input is ratified. Never fill the gap with generic Kelly." = PE-4.

**Treasury seed→cap→sweep→re-seed** `[GITBOOK]` (GITBOOK-BASE:228–238):
> "Treasury owns the virtual capital ledger... Only sweep, refund, and re-seed cross that boundary. Ledger state includes seed, equity, kill line, cap, cycle id/state, boundary events, and reconciliation verdicts. Cap is checked at rollover. Intraday cap contact does not re-anchor the book. At a valid sweep, Treasury records equity minus seed and resets virtual equity to seed; knowledge state persists. Physical broker withdrawal is not automatic. Mid-cycle top-up and live restart from kill-line remnant are forbidden."
`reconciliation_epsilon` defaults 0 USD (GITBOOK-BASE:236). Refund reserve interim `reserve_usd ~= rho * N_cycles_month * S`, GAP-0007 (GITBOOK-BASE:237). Story 5.4 birth: seed matches unique registry seed slot, opens exact at S, cycle 1 via `re_seed`, **LIVE-ready/not PAPER**; sweep only at broker-server rollover, only positive equity above seed, same cycle (BMAD-SUP:95 / B-04).

**Distinct capital concepts:** virtual ledger equity vs broker equity (reconciliation verdict); seed S / equity E / kill-line K / cap C=2.5S / runway U=E−K / daily budget D=U/n; three "seat" concepts (Topic 4). Sweep same-cycle vs next-cycle transition is a REOPEN (TND-DELTA:77 / K-29B).

---

## Topic 13 — Stop-out (definition, breakeven ambiguity, consecutive counter B=2)

**Consecutive-stop-out counter B=2** `[GITBOOK]` (GITBOOK-BASE:124): `scalper_breaker_threshold B = 2 consecutive stop-outs`. Breaker behavior (GITBOOK-BASE:246): "After the configured count of consecutive stop-outs, the affected bot moves to paper for the rest of the day and automatically resets at next open." (This is the bot-seat breaker → BENCHED path, Topic 4/7.)

**Stop-out taxonomy = PE-3 (OPEN)** `[WIKI-2026-07]` (WIKI-INV:261):
> "**PE-3 stop-out taxonomy** — what exits count for breaker projection and measured `Lbar`."
Also TND-DELTA:200 (open frontier #1): "Stop-policy forms, SL/TP computation owner, close priority, exam pinning..." BT-RECOVERED:366 (O-06 "Stop-out taxonomy (PE-3) — DESIGN").

**Breakeven-exit ambiguity:** the R-scale defines "breakeven is `0R`" (ADDENDUM:113). Whether a breakeven exit counts toward the consecutive-stop-out breaker counter or toward measured `Lbar` is exactly the unresolved PE-3 question ("what exits count for breaker projection and measured `Lbar`", WIKI-INV:261). The specific phrase "breakeven-exit ambiguity" is not verbatim, but PE-3 is its recorded locus.

**NOT found:** a precise, ratified definition of "stop-out" itself. It is explicitly an open taxonomy.

---

## Topic 14 — Alpha-decay evidence classes; 'Book sets the bar' / qualification / exam certificates / certified footprint

**Exam certificate CT-EXAM-01 — VERBATIM fields** `[GITBOOK]/[BMAD-2026-07]` (BT-RECOVERED:282–292; BT-WIKI:213–221):
```text
CT-EXAM-01: bot_id, book_profile, labeler_versions, ev_by_regime, mean_loss_r, fire_rate_band, breaker_expectation, cost_ratio
```
`mean_loss_r` = "Measured `Lbar`, used downstream by Book money rules" (BT-WIKI:218). Book-specific: "certification is not abstract" (BT-WIKI:216; INV-01 BT-RECOVERED:116).

**Examination battery (qualification metrics) — VERBATIM** `[WIKI-2026-07 registry]` (BT-RECOVERED:193–200; BT-WIKI:248–256; BT-STATUS:93–96):
```text
Walk-forward in-sample window   6 months
Walk-forward out-of-sample      1 month
Minimum OOS trades per window   200
OOS expectancy floor            0.15R after modeled costs
Monte Carlo permutations        1,000
PBO pass threshold              < 0.25
PBO dead threshold              > 0.50
```
Cost-aware formulas VERBATIM (BT-RECOVERED:204–205): `EV = p * W - (1 - p) * L - c` (FORM-0009); `p > (L + c) / (W + L)` (FORM-0010).

**Honesty acceptance SM-6 — VERBATIM** `[WIKI-2026-07]` (BT-RECOVERED:220–227; BT-STATUS:156–163):
> "multiple overfit archetypes fail; a known-good control passes; a mismatched-labeler certificate blocks live use." (`KEEP`; never implemented.)

**'The Book sets the bar' / certified footprint:** the Book's Section 3 entrance exam is the bar (Topic 1; GITBOOK-BASE:89 door "footprint"). Labeler-version parity (L10): "a labeler-version mismatch voids the certificate; affected bots stay blocked from live until recertified" (BT-STATUS:122–126; BT-WIKI:159). Certificate validity truth lives in the Trading Class-1 index, not the Backend corpus (BT-RECOVERED:319; TND-DELTA:58 / K-19).

**Alpha-decay evidence classes — NOT found** `[WIKI-2026-07]` (BT-STATUS:298):
> "Alpha-decay math | Never written down | No retrieval possible; future design."
Attic `alpha-decay-and-performance-analytics`: keep only "read-only measurement should not acquire capital/lifecycle authority"; DROP DPR/PRS ranks, global pool, continuous merit allocation (WIKI-INV:253).

---

## Topic 15 — Book/BMS validation leads (how a NEW Book/BMS proves itself before carrying money)

**Unified registration gate — VERBATIM** `[WIKI-2026-07]` (TND-DELTA:69 / K-23):
> "Unified registration serves Book→BMS and bot→Book with schema, configuration, parity, and paired-demo checks; refusal is journaled; promotion stays human."
Four autonomous checks (WIKI-INV:108): "schema, configuration, parity, and paired-demo binding; failures refuse and journal. Human promotion remains mandatory." CT-REG-01 gate ratified, field schema pending (WIKI-INV:204).

**Promotion → ADMITTED → birth path** (TND-DELTA:68 / K-22; BT-STATUS:210–220): pull, click-time server-side revalidation, atomic Class-1 write to `ADMITTED` (no intents/no ledger), then birth/LIVE at activation. Certificate is evidence only, "not permission to trade" (BT-RECOVERED:111).

**Minimal Book existence proof (Story 5.2)** `[BMAD-2026-07]` (BMAD-SUP:93 / B-02): local identity `book:{slug}`; one Trading SQLite DB; registry-owned Decimal book-instance slots outside the definition JSON; atomic `book_journal` evidence; idempotent replay; global ID policy/registry-slot catalog unresolved.

**Gap:** how a NEW *Book* (vs a bot) proves itself before carrying money is largely the schema+registration gate above; the entrance-exam battery (Topic 14) validates *bots against a Book*, not Books themselves. No separate "Book qualification battery" exists in this corpus — partial / mostly registration-gate + CT-BOOK-03 schema validation.

---

## Topic 16 — Same-tick priority; no-overnight; hold limits; dead-zone

**Same-tick priority = OPEN (explicit)** `[OP-2026-08-17]` (ADDENDUM:197):
> "What is the same-tick priority among KSA close, hold-time force-flat, protective stop, and discretionary exit?"
TND-DELTA:203 (open frontier): interleaving among "KSA close, hold-time force-flat, protective stop, and normal amendments" unresolved (also WIKI-INV:266 "Interleaving among KSA, hold-time force-flat, broker stops, and normal amendments"). Book force-flat + fast invalidation are named arms but with no ordering ruled.

**Leash chain — VERBATIM (contains hold-time force-flat)** `[GITBOOK]` (GITBOOK-BASE:90):
> "Leash escalation chain: ambient governor, day closure, bench-to-paper, chorus flag, kill-line stand-down, classed KSA, hold-time force-flat."

**No-overnight + hold-time force-flat = REOPEN** `[LEGACY/OP]` (ADDENDUM:143):
> "No completed legacy rule found. The corpus contains a no-overnight posture and explicitly records that force-flat-before-overnight was never specified. `REOPEN`. Likely relationship to maximum position age/no-overnight, but not proven."
Open question (ADDENDUM:193): "Is hold-time force-flat specifically the maximum-position-age/no-overnight rule?"

**Dead-zone (~45min session-handover no-trade) — NOT FOUND.** No mention of a session-handover dead zone or a ~45-minute no-trade window anywhere in this corpus. (The only "45" is the broker order-path budget "10–45 ms", GITBOOK-BASE:276 — unrelated.) "Session windows as trading authority" is an explicit **dead decision** (GITBOOK-BASE:375); sessions may only widen news blocks, never narrow (Topic 8). Hold limits beyond the unproven hold-time force-flat: not found.

---

## Topic 17 — Multi-currency (numeraire, cross-account aggregation, FX conversion for risk math)

**Broker equity computation (quote-currency PnL)** `[WIKI-2026-07]` (TND-DELTA:118 / K-54):
> "Broker equity must be computed from balance plus quote-currency unrealized PnL because cTrader does not supply a direct equity field; per-message money precision and side-correct bid/ask valuation are evidence. Cross-currency conversion and current protocol scaling must be freshly ratified."
Story 4.4 detail `[BMAD-2026-07]` (BMAD-SUP:87 / E-01):
> "compute balance + direct quote-currency unrealized PnL; fresh `balanceVersion`; per-message `moneyDigits`; prices integer/100000, volumes cent units, Decimal outputs; buy closes on bid, sell on ask; **cross-currency conversion remains unratified.**"

**Account numeraire:** implied USD (all scalper variables/formulas are USD — S=500 USD, K=200 USD; GITBOOK-BASE:120–121). No explicit numeraire-selection ruling recorded.

**Cross-account / cross-book aggregation:** Exposure Desk v2 and cross-book cap authority = `GAP-0008` (OPEN) `[GITBOOK]` (GITBOOK-BASE:355; WIKI-INV:280 "BMS Exposure authority beyond currency-news compilation (GAP-0008)").

**FX conversion for risk math — NOT resolved:** explicitly "cross-currency conversion remains unratified" (BMAD-SUP:87) / "must be freshly ratified" (TND-DELTA:118). No conversion mechanism, rate source, or aggregation formula exists in this corpus.

---

## Carry-forward vs Do-not-revive rulings (corpus-level, risk-relevant)

- **Disposition ladder** (TND-README:19–25): `BASELINE`/`KEEP`/`RECONFIRM`/`REOPEN`/`DROP`.
- **DROP list D-01..D-13** (TND-DELTA:180–194): esp. D-07 globally-uniform stop service; D-08 EAV for Book attributes (refused by CT-BOOK-03); D-09 any SQS expansion as snapshot/signal quality score or execution authority; D-10 silent canonical-feed failover + independent live/demo ordering; D-11 automatic promotion/resume; D-13 old proof-local SQLite owner guards.
- **Backtest DROP** (BT-RECOVERED:393–407): six-clamp, multiplier stack, equity bands, slot caps, old circuit breaker; DPR/PRS ranking/tiers/global pools/slot auctions; session windows as authority; "BE at +1R" and old SL/TP service (BT-RECOVERED:261); old WF2 Stages G–I.
- **Exit/stop re-anchoring** (BT-RECOVERED:250–261): do NOT inherit old `BE at +1R`, old SL/TP service, old kill-check ordering, six-clamp, multiplier stack, equity bands, slot caps.

## Open items (PE-* and named GAP-*, risk-relevant) as recorded

- **PE-3** stop-out taxonomy — what exits count for breaker projection + `Lbar` (WIKI-INV:261; BT-RECOVERED:366).
- **PE-4** trust-bounded cost-aware Kelly input; FORM-0005 incomplete by design (WIKI-INV:262,124; TND-DELTA:90).
- **PE-5** KSA trigger→level→effects matrix incl. fail-closed unknown/unmapped = GAP-0015 (BMAD-SUP:101; BT-RECOVERED:388).
- **PE-7** position fate at rollover/sweep/kill-line/paper; open positions force `unknown` reconciliation; 2026-07-28 ruling permits PE-7-*neutral* work only (no auto position action) but leaves flatten-vs-carry open (TND-DELTA:89 / K-36; WIKI-INV:263; BMAD-SUP:98 / B-07). Provenance of the 2026-07-28 memo is `RECOMMENDED`, not fully logged (TND-DELTA:156 / C-04).
- **PE-8** stop-policy version pinning into CT-EXAM-01 (BT-RECOVERED:124 INV-09, O-08:368).
- **GAP-0007** refund reserve `rho`/cycles estimator; refund dormant (GITBOOK-BASE:237).
- **GAP-0008** Exposure Desk v2 + cross-book caps (GITBOOK-BASE:355).
- **GAP-0012** certified leash-event / chorus frequency `F_CHORUS` (GITBOOK-BASE:358; BT-RECOVERED:308).
- **GAP-0015** KSA trigger→level matrix (GITBOOK-BASE:360; WIKI-INV:134).
- Failed-cycle closure / intraday-cap-vs-rollover / next-re-seed authority (TND-DELTA:176 / C-24, open frontier #15 TND-DELTA:214).

---

## Contradictions (recorded, not adjudicated)

1. **Book-mode namespace mixing** (TND-DELTA:154 / C-02; WIKI-INV:290): wiki prose says active modes = LIVE/PAPER with BENCHED a seat state and STOOD_DOWN reserved, but CT-BOOK-02/CT-BMS-02/CT-PAPER-01 enum tables still mix all four into `book_id`-keyed modes. `REOPEN` — define separate enums.
2. **Book-mode cannot express per-bot breaker** (GITBOOK-BASE:403 / T-06): CT-PAPER-01 has optional `bot_id` but CT-BOOK-02/CT-BMS-02 are keyed only by `book_id`; a mixed book (one bot benched, others live) is not representable.
3. **Birth vs paper balance** (TND-DELTA:167 / C-15; BMAD-SUP:111): wiki Treasury says birth freezes paper balance at `S`; Story 5.4 says birth is LIVE-ready/not PAPER; Story 5.8 freezes only on a later fail-mechanism transition. `REOPEN` (post-AD-28 model is the candidate, not automatic authority).
4. **SQS meaning drift** (TND-DELTA:190 / D-09; WIKI-INV:298): wiki called SQS "snapshot quality score"; operator ruling 2026-08-17 = **Spread Quality Sensor**; the six-component aggregate is drift, not SQS.
5. **Exit authority layering** (ADDENDUM:148–160): GitBook "bot owns exit organs" vs current QMF "a confluence contains no exit; exits/sizing/risk are Book territory." Item 3 (current operator vocabulary) governs the authoring boundary; exact contract is `DESIGN`.
6. **FORM-0006 units** (ADDENDUM:119; GITBOOK-BASE:425 / T-12): `R_max_usd <= B*b*Lbar` compares a USD name with an R/ratio RHS; do not normalize until repaired.
7. **Cycle termination after kill-line** (GITBOOK-BASE:431 / T-13; TND-DELTA:176 / C-24): seed-to-cap cycle undefined for a failed sub-cap cycle; same-cycle sweep (BMAD proof) vs next-cycle reset (wiki/GitBook scenario language) unreconciled — `REOPEN` (TND-DELTA:77 / K-29B).
8. **Dynamic SL/TP owner** — placement ruled to Book money-rule grammar (TND-DELTA:88), but computation owner / close priority / exam pinning / boundary position fate all remain open (same line, precision boundary).
9. **KSA↔BMS cyclic authority** (TND-DELTA:170 / C-18; GITBOOK-BASE:409 / T-08): BMS owns KSA policy while KSA owns/persists protection state; init/recovery ordering unseparated — preserve MIS→KSA→Adapter funnel, separately define policy source vs state writer.
10. **CT-BMS-01 event conflation** (TND-DELTA:175 / C-23; GITBOOK-BASE:397 / T-05): request vs approved Treasury transaction vs recorded event conflated on one contract; treasury-event path drawn inconsistently (Scalper→Treasury vs Treasury→BMS vs Scalper→BMS→Treasury).

---

## Not-found list (checklist items with no / only-partial evidence in THIS corpus)

- **Topic 1:** exact VERBATIM field lists of CT-BOOK-01 / CT-BOOK-02 / CT-BOOK-03 (only identifiers, statuses, and the `requested_r`-is-a-proposal note; no field enumeration).
- **Topic 3:** explicit ruling that one Book may bind accounts at *several venues*; explicit Book↔BMS numeric cardinality (multi-venue is out of V1).
- **Topic 5:** the specific "scalping-book-v2 = NEW Book, never inherits v1 ledger" rule (no cross-version Book ledger-inheritance statement).
- **Topic 8:** before/after news window *minutes*; numeric event-severity tiers; explicit open-position behaviour during news (all deferred; only qualitative "unknown high-impact blocks conservatively").
- **Topic 11:** an *enforced* correlation/chorus threshold (`F_CHORUS` is null under GAP-0012 — recorded/computed only).
- **Topic 13:** a ratified definition of "stop-out" and explicit resolution of the breakeven-exit-counts-as-stop-out question (both are open PE-3).
- **Topic 14:** alpha-decay evidence classes ("never written down; no retrieval possible").
- **Topic 15:** a distinct Book-qualification battery for a NEW *Book* (validation = registration gate + CT-BOOK-03 schema only; the exam battery validates *bots*, not Books).
- **Topic 16:** dead-zone / ~45-minute session-handover no-trade window (absent); ratified hold-time force-flat / max-position-age / no-overnight rule (posture only, REOPEN).
- **Topic 17:** account-numeraire selection ruling; FX-conversion mechanism/rate-source for cross-currency risk math; cross-account aggregation formula (all "unratified" / GAP-0008).
