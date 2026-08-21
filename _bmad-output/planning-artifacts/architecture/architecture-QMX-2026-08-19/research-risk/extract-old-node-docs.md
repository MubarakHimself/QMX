# Extractor dossier — old trading-node docs/standards corpus (risk sitting, GAP-0039..0046)

**Extractor scope (corpus):** `C:/Users/Mubarak/Documents/QMX/` under `trading-node/`, `standards/`, `references/`, `stack/`, `ops/` (READ-ONLY evidence).
**Layer labels used below (I record, never rank):**
- **L-STD** = old trading-node ratified standards (`standards/*.json`, `status: ratified` / `ratified-by-story-5-x`; `ratified_date` mostly 2026-07-26/27; all cite architecture spine `architecture-QMX-2026-07-20`). This is the OLD node build's ratified layer, *below* current Desktop/QMX rulings and roughly contemporaneous with late wiki.
- **L-CODE** = old trading-node Python/JSON implementation (`trading-node/qmx_trading_node/*.py`, `registry_census.json`), same build generation as L-STD.
- **L-UI** = `references/ui-exploration/*` console design cut, **exploratory** v0.1 (2026-07-23) / v0.2 (2026-07-23); self-labeled "exploratory state model" / "proposed" — weakest layer, records open conflicts rather than rulings.
- All L-STD/L-CODE files name `wiki/...` source_evidence — the wiki itself is a *different* extractor's corpus; I cite only the reference pointers I can see, not wiki bodies.

Money/time discipline is global in this corpus: binary floats forbidden on money/price/equity/sizing; canonical decimal text only; ambient datetime/randomness forbidden (`labeler-catalog-ratification.json:400-405`).

---

## Topic 1 — Book schema (CT-BOOK-01/02/03, versioned book-type schema, seven doors)

**FOUND — CT-BOOK-03 book-type schema (L-STD, `standards/ct-book-03-book-type-schema.json`, ratified Story 5.1, authority AD-24/25/26, AR-9/18/33, wiki ADR-0002).**

Template sections are **exactly ordinals 0–5** (six sections; **there is no "seven doors" enumeration in this corpus** — see below). Verbatim keys (`:40-71`):

```
0 charter | 1 footprint | 2 money_rules | 3 entrance_exam | 4 leash_chain | 5 capacity_and_sweep_mechanics
```
Section 6 is explicitly forbidden (`:72-76`): `"Section 6 is undefined in the ratified corpus and must not appear in CT-BOOK-03 book-type definitions."`

Required top-level fields of a book-type definition (`:82-91`):
```
standard_id, book_type_id, book_type_version, template_sections,
type_structure, storage, permitted_attribute_set, registry_numeric_authority
```
Key field rules (verbatim patterns, `:96-118`):
```
book_type_id      pattern ^book-type:[a-z0-9][a-z0-9-]*$
book_type_version pattern ^[0-9]+[.][0-9]+[.][0-9]+$   (semantic version)
template_sections minItems 6 maxItems 6, ordinals 0-5 with the ratified keys
type_structure.grammar const "book-template-sections-0-5"
type_structure.book_instance_creation const false
type_structure.book_type_specific_values_inline const false
```
Storage discipline (`:131-233`): design const `typed_core_columns_plus_sparse_ratified_keys_json_bag`; `eav: false` ("EAV is structurally invalid"); typed core column REQUIRED for every filtered field; JSON bag may NOT be a primary filter surface or hold filter authority; sparse bag keys `key_policy const ratified_keys_only`; permitted qualifiers `[inert, measured, informational]`. Hot attributes require expression-index promotion.

**Numeric authority (load-bearing for money topics):** authoritative numeric values may **never be embedded inline**; they are registry-owned under `owner_scope const "book_instance"`, referenced by (`:196-217`):
```
registry_ref pattern: ^registry://book-instance/[{]book_id[}]/.../[{]slot_id[}]$
```
Refusal codes (`:243-249`): `CT_BOOK_03_SCHEMA_VIOLATION`, `..._NUMERIC_AUTHORITY_REFUSED`, `..._STORAGE_REFUSED`, `..._SECTION_REFUSED`, `..._STANDARD_INVALID`.

**FOUND — Book minimal existence / identity (L-STD, `standards/book-definition-minimal-existence.json`, Story 5.2).**
- `book_id local_format: "book:{slug}"`, stable, derived from caller lowercase slug; ambient randomness / wall-clock identity forbidden (`:19-27`).
- Class-1 tables: `qmx_book_definitions`, `qmx_book_registry_slots` (`:30-33`); per-book database files forbidden (`:35`); single trading-node SQLite DB.
- Typed core columns of a book definition (`:45-52`): `book_id, book_slug, book_type_id, book_type_version, template_section_set, definition_hash`.
- Authoritative numeric storage: `qmx_book_registry_slots.value_decimal_text`, canonical finite decimal text, binary float forbidden (`:54-63`).
- Records evidence: journal `book_journal`, event `book_definition_created`, atomic with class-1 creation, writer `RecordsStore.commit_decision_with_evidence` (`:65-70`).

**Seven doors — CONTRADICTED/PARTIAL (not enumerated here).** The concept exists but is *never enumerated* in my corpus. Only surface references: L-UI `screen-and-state-inventory-v0.2.md:177` "intent through seven doors to command/fill/refusal"; `qmx-console-ui-backend-cut-v0.2.md:149,154` "seven-door outcomes … door decision"; `object-lifecycle-bot.md:49` bot activity state `REFUSED_BY_DOOR`; L-STD `ct-mis-01-degradation-visibility.json:38,51` field `door_hard_block`; `labeler-catalog-ratification.json:204` "downstream doors fail closed". Book detail shell has a **"Doors"** tab (`qmx-console-experience-architecture-v0.2.md:139`). The names of the seven doors are **not in this corpus** (wiki-owned).

**CT-BOOK-01 / CT-BMS-04: NOT FOUND** in this corpus (see Not-found list). CT-BOOK-02 is referenced as the mode-registry write contract but its own schema file is not here (`ct-book-03...json:33-38` lists CT-BOOK-02 among `contracts_not_ratified_here`).

---

## Topic 2 — BMS schema (CT-BMS-*), BMS-owns vs Book-owns

**FOUND — CT-BMS contract inventory present in this corpus:**
- **CT-BMS-01** treasury boundary event — enum `{sweep, refund, re_seed}` (`treasury-virtual-ledger-and-birth-mechanics.json:60-73`, `closed-treasury-boundary.json:21-45`).
- **CT-BMS-02** mode-registry READ contract — producer BMS, consumer "KSA and read consumers", returns `book_id, mode, updated_at_utc`, `mutation_authority_transferred: false` (`mode-registry-authoritative-book-mode-map.json:56-66`).
- **CT-BMS-03** reconciliation report — owner `reconciliation.py`, producer Treasury / consumer BMS (`reconciliation-reports-and-technical-kill.json:1-25`, see Topic 10/13).
- **CT-BMS-05** Records stream append / label-based fill attribution (`label-based-fill-attribution-and-journaled-fills.json:11,25-36`; `ad-41-stream-register.json:63-157`).
- **CT-BOOK-02** book-mode WRITE contract (`mode-registry-...json:33-55`).

**Ownership split (FOUND):**
- **Book (definition) owns:** identity (`book_id`), book-type definition, template sections 0–5, and per-instance registry numeric slots (`qmx_book_registry_slots`, owner_scope `book_instance`) — `book-definition-minimal-existence.json:40-64`.
- **BMS owns (all keyed by `qmx_book_definitions.book_id` foreign identity):** the mode registry (`qmx_book_mode_registry`, `qmx_book_mode_transitions`; owner "BMS mode registry", `mode-registry-...json:21-32`); the Treasury virtual ledger + cycles (`qmx_treasury_virtual_ledgers`, `qmx_treasury_cycles`; owner "BMS Treasury", `treasury-...json:20-31`); reconciliation reports / technical-kill (`reconciliation-...json:17-24`); Records streams (Records is "Records (BMS)", `ad-41-stream-register.json:63-157`).
- BMS is registry component **COMP-BMS** (`registry_census.json:157`). Book/BMS/KSA *decision logic* is repeatedly held out of the sensing layer (`ct-mis-01-degradation-visibility.json:122` `book_ksa_bms_decision_logic: false`).

---

## Topic 3 — Cardinalities (Book↔BMS, bot↔Book, Book↔account/venue)

**bot ↔ Book — FOUND (L-UI + L-CODE):** "A bot is certified against a particular book profile and joins a **book-owned roster seat**" (`object-lifecycle-bot.md:19-31`); certification is **book-specific** (`:79`). One Book holds a roster of bots — `roster_capacity` provisional **6** bots (`registry_census.json:601-612`), distinct from `max_concurrent_live_bots` = **3** (`N_live_max`, DEC-0028, `registry_census.json:162-174`). Bots may have "previous memberships where evidence exists" (`object-lifecycle-bot.md:30`). So **Book 1 : many bots**; a bot's certification binds it to one book profile at a time.

**Book ↔ account — FOUND (L-UI):** account detail shows "**books bound to the account**" (plural) and "live and paired demo bindings" (`qmx-console-experience-architecture-v0.2.md:159-161`) → **one account : many books**. Paired-demo binding is **per-live-account**, "exactly one demo pair required for live" (`paired-demo-binding-per-live-account-binding.json:15-27`). Book lifecycle Facet 4 execution-readiness inputs include "account binding, paired demo binding for PAPER" (`object-lifecycle-book.md:47-52`).

**Book ↔ BMS — PARTIAL:** BMS is a single subsystem (COMP-BMS) whose mode/treasury/reconciliation state is per-`book_id`; effectively **BMS 1 : many Books** (each Book has one mode row, one treasury ledger row + cycle rows). No explicit "one Book owns several BMS" statement exists — the direction is inverted (one BMS, many books).

**Book ↔ venue / accounts-at-several-venues — NOT FOUND / OUT OF SCOPE.** `venue_platform_instrument_encodings` is an explicit non-goal / unresolved across multiple standards (`ct-book-03...json:258`, `book-definition-...json:88`, `ad-41-stream-register.json:29` `venue_encodings: null`). No evidence a Book may bind accounts at several venues.

---

## Topic 4 — Lifecycle states & modes; seat-state vs book-mode split; which enum lives where

**FOUND — Book mode enum (L-CODE `mode_registry.py:38-40`, L-STD `mode-registry-...json:42-49`):**
```
V1_BOOK_MODES        = {"LIVE", "PAPER"}
RESERVED_BOOK_MODES  = {"BENCHED", "STOOD_DOWN"}   # reserved, GAP-0015, not V1
```
CT-BOOK-02 write accepts only `LIVE`/`PAPER`; reserved modes refuse with `MODE_REGISTRY_RESERVED_BOOK_MODE` (`mode_registry.py:342-354`; `mode-registry-...json:68-76`). Mode write required fields: `book_id, mode, reason, trigger_decision (DEC-[0-9]{4}), effective_at_utc`; event `book_mode_changed` on `book_journal` (`mode-registry-...json:33-55`). Tables: `qmx_book_mode_registry` (current, non-deletable) + `qmx_book_mode_transitions` (append-only).

**FOUND — Book-mode transitions (L-UI `object-lifecycle-book.md:23-32`, exploratory):**
```
PAPER <-> LIVE
- birth currently creates the book in PAPER;      [<-- see CONTRADICTION vs Story 5.4]
- warm-up may transition it to LIVE at an eligible rollover;
- kill-line stand-down returns it to PAPER; and
- book-level BENCHED and STOOD_DOWN are reserved, not current V1 modes.
```

**FOUND — Seat-state vs book-mode SPLIT (L-UI `object-lifecycle-bot.md:34-51,77-84`):** seat state is a **bot-level** facet, distinct from book mode:
```
Seat states: paper-phase seat (after examination/gate) | LIVE | BENCHED
  (BENCHED behaves as paper until next-open automatic return to LIVE)
Invariant: "A BENCHED bot does not change the book mode."
Invariant: "Breaker auto-reset does not erase the bench event."
Bot trading-activity read-model: TRADING | POSITION_OPEN | WAITING | REFUSED_BY_DOOR | NO_SESSION_ACTIVITY
```
So: **book-level** enum LIVE/PAPER (+reserved BENCHED/STOOD_DOWN) lives in the mode registry; **bot/seat-level** BENCHED lives on the roster seat and does NOT write book-level BENCHED (`frozen-counterfactual-paper-semantics.json:43-49` `book_level_benched_write: false`).

**FOUND — CT-PAPER-01 transition kinds tie the split together (`frozen-counterfactual-paper-semantics.json:33-49`):**
```
kill_line_stand_down : book-scoped, bot_id NOT required, LIVE -> PAPER
breaker_bench        : bot-scoped,  bot_id required,     LIVE -> BENCHED (no book-level benched write)
```
Accepted mode-transition reason markers (L-CODE `mode_registry.py:43-58`): `birth-in-paper, warm-up-to-live, exam-to-paper, bot breaker bench, breaker bench, activation, treasury boundary, sweep, re_seed` — these are `RELOCATED_REASON_MARKERS` (their transition semantics live outside Story 5.3 → `MODE_REGISTRY_RELOCATED_TRANSITION`).

Book faceted state (L-UI `object-lifecycle-book.md`): Facet1 Release `DISCOVERED→FETCHING→VERIFYING→INSTALLING→INSTALLED` (+`REFUSED|SUPERSEDED|OUTCOME_UNKNOWN`); Facet3 Capital `AVAILABLE|CONSTRAINED|UNAVAILABLE|UNKNOWN`; Facet4 Execution `READY|RECOVERING|BLOCKED|UNKNOWN`; Facet6 Cycle; Facet7 Attention. Finished-goods delivery adds mode `WAITING_LIFECYCLE_BOUNDARY` "installed, but a warm-up/rollover rule applies" (`flow-004-finished-goods-delivery.md:60-66`).

---

## Topic 5 — Book versioning + compatibility (v2 = NEW Book, never inherits v1 ledger)

**PARTIAL — FOUND (versioning) / NOT-FOUND (the exact "never inherits v1 ledger" rule).**
- Book type carries `book_type_version` semver (`ct-book-03...json:101-105`); book definition stores `book_type_version` + `definition_hash` (`book-definition-...json:45-52`); conflict refusal `BOOK_DEFINITION_CONFLICT` when a stable `book_id` "already exists with different definition or slot evidence" (`book-definition-...json:76`).
- Bot analogue rule (nearest verbatim to "new version = new object"): "Changing behaviorally consumed specification/configuration **mints a new bot specification version**" (`object-lifecycle-bot.md:84-85`); bot identity/artifact versions immutable (`:6-8`).
- Schema-evolution discipline governs table/version drift with forward-only migrations and required triggers (`schema-evolution-discipline.json`).
- L-UI records that "Update, supersession, rollback, and partial-install policy are **not defined**" (`qmx-console-experience-architecture-v0.2.md:290`); book Facet1 has terminal `SUPERSEDED`.
- **The specific claim "scalping-book-v2 is a NEW Book that never inherits the v1 ledger" is NOT stated verbatim in this corpus.** What IS present: per-book treasury ledger keyed by `book_id` with birth as cycle 1 only (`treasury-...json:60-73`), so a different `book_id` would necessarily have its own fresh cycle-1 ledger — but this is inference, not a ratified sentence here.

---

## Topic 6 — Exit ownership (bots own exits vs Book owns exits; forced exits; fast invalidation; dynamic SL/TP; SL-TP authority)

**PARTIAL — the ownership PRINCIPLE is FOUND; concrete exit-organ / SL-TP mechanics are NOT in this corpus.**
- Load-bearing invariant (L-UI `object-lifecycle-bot.md:80`): **"Bot code owns market intent; the book owns admission and sizing."** Complementary: intent flows "through seven doors to command/fill/refusal" (`screen-and-state-inventory-v0.2.md:177`).
- Book Facet5 Protection (L-UI `object-lifecycle-book.md:54-58`): "Book effects derive from global KSA and scoped directives. The book does not own KSA de-escalation."
- Adapter command vocabulary that could execute exits (L-STD `connection-pool-...json:43-46`, `paired-demo-...json:87-91`): `place_order, cancel_order, close_position, close_all`.
- **NO SL/TP fields, no dynamic-stop/trailing logic, no "fast invalidation", no "force-flat" definition, no "who moves the stop and when" exists in trading-node code or standards.** `book-template` section 4 is named `leash_chain` (`ct-book-03...json:62-65`) and L-UI shows "leash events" (`qmx-console-ui-backend-cut-v0.2.md:149`), but leash mechanics are not specified here. Position-safety / SL-TP authority = **NOT FOUND** (wiki/other-corpus territory).

---

## Topic 7 — Paper mode (bench-to-paper, paired demo, duplicate-order prevention, live↔paper, evidence comparability)

**FOUND — CT-PAPER-01 frozen-counterfactual paper semantics (L-STD `frozen-counterfactual-paper-semantics.json`, Story 5.8, owner `paper_mode.py`).**
Required transition fields (`:16-29`):
```
book_id, from_mode, to_mode, frozen_balance_decimal, trigger_event_id, trigger_kind,
transition_ratified, paired_demo_binding_record, sensing_continuation_proof,
paper_trading_continuation_proof, occurred_at_utc   (optional: bot_id)
```
- Transition kinds `kill_line_stand_down` (book-scoped LIVE→PAPER) and `breaker_bench` (bot-scoped LIVE→BENCHED) — see Topic 4.
- **Frozen balance** immutable after acceptance, canonical decimal, no hand adjustment (DEC-0014); refusal `PAPER_FROZEN_BALANCE_HAND_ADJUSTMENT_REFUSED` (`:50-60,84`).
- **Paper gains are evidence only, never CT-BMS-01 Treasury events**: `paper_gains_enter_ct_bms_01: false`; refusal `PAPER_GAIN_NOT_TREASURY` (`:68-72,85`).
- Continuation evidence required: `sensing_continuation_proof` + `paper_trading_continuation_proof`; paired-demo binding story 4.6; **live-drift-check exclusion required** (`:61-67`).
- Idempotency: duplicate identical transition returns existing proof; conflicting refuses (`:73-76`).

**FOUND — Paired demo binding (L-STD `paired-demo-binding-per-live-account-binding.json`, Story 4.6, "connection_manager owns pairing").**
- Live binding requires demo-pair candidates, **exactly one** demo pair, verification evidence (`:14-27`).
- Demo binding **excluded from live technical-kill drift checks** — "paired demo binding is the fail-mechanism paper route, not a live drift target" (`:29-33`).
- Proof record `paired_demo_binding` fields (`:50-70`) incl. `live_binding_id, demo_binding_id, verification_state, routing_consumers`; routing consumers = `kill_line_stand_down, breaker_bench_paper_routing, promotion_safety_checks`.
- **Duplicate-order prevention (shared-account command merge, `:85-97`):** deterministic ordering by `book_sequencer_sequence`; `duplicate_sequence_refused: true`, `missing_sequence_refused: true`, `stable_tie_refusal: true`; allowed kinds `place_order, cancel_order, close_position, close_all`.
- Secret boundary: metadata only, `secret_ref`, raw credentials forbidden (`:80-84`).

**FOUND — evidence comparability:** reconciliation `account_binding_modes: [live, demo, paper]`; demo/paper bindings excluded from live drift only with verified Story 5.8 exclusion evidence (`reconciliation-...json:41-48,103`). Exam↔live labeler parity required (`labeler-catalog-...json:64`).

---

## Topic 8 — News protection (windows, severity tiers, currency→instrument mapping, open-position behavior, overrides)

**NOT FOUND in this corpus.** No news-window / economic-calendar blackout mechanics exist in `trading-node/`, `standards/`, `stack/`, or `ops/`. The only adjacent artifact is L-UI Activity category 8 "**calendar**, feed, and supervision events" (`qmx-console-experience-architecture-v0.2.md:194`) — a display category, no before/after minutes, no severity tiers, no currency→instrument mapping, no open-position override policy. (`news` hits in `references/hermes/llms-full.txt` are unrelated third-party tooling docs, not QMX.)

---

## Topic 9 — SQS / spread-quality sensing (formula, inputs, thresholds, cadence, hysteresis, WHY)

**FOUND — full SQS contract, VERBATIM (L-STD `labeler-catalog-ratification.json:294-363`, Story 3.1, contracts CT-MIS-01/02/CT-EXAM-01).**
```
sqs_contract:
  meaning: "snapshot quality score"
  formula_id: sqs_weighted_component_floor_v1   (deterministic)
  scale_basis_points: 10000
  minimum_reachable_score_basis_points: 1
  required_inputs (each 0..10000 bp):
    spread_quality_bp, gap_quality_bp, liquidity_quality_bp,
    feed_quality_bp, sensor_freshness_quality_bp, regime_quality_bp
  weights_basis_points:
    feed_quality_bp        2500
    spread_quality_bp      2000
    gap_quality_bp         1500
    liquidity_quality_bp   1500
    sensor_freshness_quality_bp 1500
    regime_quality_bp      1000        (weights sum = 10000)
  score_basis_points_formula: floor(sum(component_quality_bp * component_weight_bp) / 10000)
  score_number_formula:       score_basis_points / 10000
  unreachable_input_marker: "sqs_unreachable"
  unreachable_behavior: { sqs_hard_block: true, ordinary_degradation: false, trade_authority: false }
  refusals: SQS_INPUT_REFUSED, SQS_UNKNOWN_COMPONENT, SQS_FORMULA_DRIFT
```
- Weights **must sum to scale (10000)** or `SQS_FORMULA_DRIFT` (L-CODE `labeler_catalog.py:226-228`). Reachable score below `minimum_reachable_score_basis_points` refuses (`labeler_catalog.py:230-236`).
- Producing labeler `snapshot_quality_score_v1` publishes `sqs_score, sqs_hard_block`; on failure `sqs_unreachable_hard_block` (`labeler-catalog-...json:206-233`).
- **WHY (authority note, verbatim):** "SQS is deterministic evidence only; **it does not authorize or execute a trade**" (`labeler-catalog-...json:232`). Unreachable SQS → **hard door block** (`ct-mis-01-degradation-visibility.json:48-54`).
- **Component thresholds (spread-quality sensing inputs), VERBATIM (`labeler-catalog-...json:99-205`):**
```
spread_state_v1:  normal_max_spread_points 12, elevated_max_spread_points 25, extreme_above_spread_points 25
gap_event_v1:     max_expected_tick_gap_ms 1500, max_expected_bar_gap_count 1
liquidity_stress_v1 (fitted): spread_stress_quantile_bp 9500, depth_stress_quantile_bp 500
feed_state_v1:    fresh_max_age_ms 1000, stale_max_age_ms 5000, dead_above_age_ms 5000
regime_classifier_v1 (trained): allowed_regimes [trend, range, chaos], confidence_scale_bp 10000
```
**Cadence / hysteresis:** NOT specified in this corpus (SQS is defined per-snapshot; no cadence interval or hysteresis band is given). CT-MIS-01 published fields incl. `sqs_score, sqs_hard_block` (`labeler-catalog-...json:36-49`).

---

## Topic 10 — Kill switch / KSA (authority, scopes, escalate-only + human de-escalate, effect vocabulary, adapter interaction)

**FOUND (levels + authority model) — but KSA *protection/matrix logic* is an explicit non-goal across this build (deferred).**
- **KSA levels enum (L-CODE `registry_census.json:318-336`), VERBATIM:** `["GREEN","YELLOW","ORANGE","RED","BLACK"]`, symbol `KSA_LEVELS`, DEC-0043, `non-configurable`, `"Global capability; book profiles select behavior."`
- **Authority / escalate-only + human de-escalates (L-UI `flow-002-a1-recovery.md`, exploratory):** header "**Authority: operator-only de-escalation of KSA**" (`:5`); book "does not own KSA de-escalation" (`object-lifecycle-book.md:57`). Recovery ("A1") requires the operator to open the active KSA event and submit **one idempotent** command; server revalidates against expected KSA event/version (`flow-002:24-38`). Non-overridable blockers: unexplained reconciliation drift, unknown broker state, incomplete gap recovery, dead feed, unknown KSA event/version (`:40-48`). Outcomes `RECOVERED|STILL_PROTECTED|REJECTED|PENDING|OUTCOME_UNKNOWN` (`:50-60`).
- **Scopes (L-UI `flow-002:66-69`):** KSA event carries "affected **pairs/books/accounts**", trigger, scope, effects, enforcement completion. Refusal is journaled and "does not halt unrelated books" (`object-lifecycle-book.md:98`).
- **Effect / adapter vocabulary:** "adapter **drain**/enforcement acknowledgments" (`flow-002:73`); adapter command kinds `place_order, cancel_order, close_position, close_all` (`connection-pool-...json:43-46`, `paired-demo-...json:87-91`). Note `ksa_drains: false` is a *non-goal* of the connection-pool story (`connection-pool-...json:67`), i.e. drain execution not implemented there.
- **KSA as sensing consumer:** MIS fans identical evidence to **Book and KSA**; "ksa_receives_information_only: true" (`ct-mis-01-fan-out-transport.json:42-45`, `ct-mis-01-live-snapshot-publication.json:96-99`, `ct-mis-01-degradation-visibility.json:86-93`).
- **Audit stream:** `ksa_audit_log` — Records (BMS) produced, CT-BMS-05, Class-2 append-only (`ad-41-stream-register.json:120-137`; `coding-standards.md:37`; `ci-gates.json:270`).
- **DEFERRED / non-goal here:** `ksa_matrix` (`mode-registry-...json:84`), `ksa_protection_logic` (`rollover-only-sweep.json:85`, `closed-treasury-boundary.json:92`), `ksa_or_adapter_resume_authority` (`reconciliation-...json:117`), `kill_line_detector` (multiple). The KSA **decision matrix and scope→effect table are not implemented in this corpus.**

---

## Topic 11 — Correlation ledger / correlation rules (computed vs enforced)

**FOUND (stream exists) — but computed-vs-enforced semantics are OPEN in this corpus.**
- **`correlation_ledger` stream** — Records (BMS), CT-BMS-05, Class-2 append-only (`ad-41-stream-register.json:139-157`). Note verbatim: `"correlation values are not money"`, and `open_notes`: "payload/event-type details **remain OPEN** in the draft-streams-and-entities contract pass; this row only carries the AD-41 register scope and Records ownership boundary." Table DDL (append-only, Records-only insert) in `schema-evolution-discipline.json:202-208`.
- **Deferred correlation SCREEN:** registry slot `registration_screen_thresholds` — "Deferred **correlation, deduplication, and classification screen** slots; no autonomous V1 threshold is supplied" (`registry_census.json:652-664`).
- **Caution — a DIFFERENT "correlation":** `label-based-fill-attribution-...json:17-24` defines `correlation_rules` but these are **fill-attribution** rules (bot-ownership label / `clientMsgId` matching, `max_label_length 100`), NOT position/risk correlation. Do not conflate.
- **Enforcement thresholds = NOT FOUND** (no correlation cap / cluster-limit value is ratified here).

---

## Topic 12 — Money ladder + R (FORM-0004, FORM-0006, variables/units, seat/offer/take, treasury seed-to-cap+sweep, distinct capital concepts)

**FOUND — complete money-ladder registry, VERBATIM (L-CODE `registry_census.json`, Story 1.4; sources incl. `wiki/scenarios/scn-0001-money-ladder.md`; all DEC-0029/0030).**

Variables (`:15-350`):
```
S   scalper_seed_capital        = 500  USD    (DEC-0029; S > K; operator-countersigned)
K   scalper_kill_line           = 200  USD    (fixed within the cycle)
cap_multiple scalper_cap_multiplier = 2.5 ratio (Cap C = S * cap_multiple)
n   scalper_runway_divisor      = 5    count  ("floor-trader discipline number")
B   scalper_breaker_threshold   = 2    consecutive_stopouts ("before bench-to-paper")
b   scalper_budget_shaping_factor = 2  ratio  (offer-per-seat coefficient)
Lbar scalper_mean_loss_r        = measured_per_bot_at_exam, units R; reference 0.35R
     ("0.35R is a reference expectation only; never an inherited bot default"; configurable:false)
v_cost viability_cost_fraction_max = 0.10 fraction_of_R (DEC-0030)
eps_recon reconciliation_epsilon = 0 USD (DEC-0015; operator review before non-zero)
N_live_max max_concurrent_live_bots = 3 bots (DEC-0028)
```
Formulas (`:352-557`), VERBATIM:
```
FORM-0001 cap_equity          C = cap_multiple * S
FORM-0002 runway              U = E - K
FORM-0003 daily_loss_budget   D = U / n
FORM-0004 offer_per_seat      offer_R_usd = D / (B * b * Lbar)
FORM-0005 take_per_seat       take_R_usd = min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)   [gap PE-4]
FORM-0006 r_max_ceiling       R_max_usd <= B * b * Lbar
FORM-0007 viability_floor     round_trip_cost_R / expected_edge_R <= v_cost
FORM-0008 refund_reserve      reserve_usd ~= rho * N_cycles_month * S   [gap GAP-0007, rho/N null]
FORM-0009 expectancy_in_r     EV = p * W - (1 - p) * L - c
FORM-0010 break_even_prob     p > (L + c) / (W + L)
```
**Variable meanings/units for FORM-0004/0006:** `D` = daily loss budget in USD (= runway/n, runway = equity E − kill-line K); `B` = consecutive-stop-out breaker threshold (count, =2); `b` = budget-shaping ratio (=2); `Lbar` = mean loss per trade in **R** (measured per bot at exam; ref 0.35). So `offer_R_usd` and `R_max_usd` are per-seat USD sizes. FORM-0004/0006 also enforce `Lbar > 0` else unresolved (L-CODE `registry.py:395-436, 433-475`); numeric authority is registry-owned (never inline). Seat chain wired S→U→D→offer→take in `registry.py:824-840`.

**seat / offer / take mechanics — FOUND:** `offer_R_usd` (per-seat budget allowance) → `take_R_usd = min(offer, cost-aware-Kelly)`; Kelly input `trust_bounded_cost_aware_kelly_R_usd` is `PE-4`/unresolved (`registry.py:420-437`; `registry_census.json:438-453`). Invariant "the book owns admission and **sizing**" (`object-lifecycle-bot.md:80`); "**Unused risk budget is not redistributed within the cycle**" (`object-lifecycle-book.md:100`).

**Treasury seed→cap + sweep — FOUND (L-STD Stories 5.4/5.5/5.6; L-CODE `treasury.py`).**
- **Birth (5.4):** re_seed opening cycle 1, `cycle_id = "treasury-cycle:{book_id}:1"`, seed must equal the book's registry seed slot; result `live_ready: true, paper_mode_created: false` (`treasury-...json:32-98`). Tables `qmx_treasury_virtual_ledgers` (one current row: `seed_decimal_text, current_virtual_equity_decimal_text, current_cycle_id`) + `qmx_treasury_cycles` (`treasury.py:137-160`).
- **Sweep (5.5, rollover-only):** `sweep = rollover_equity_decimal - seed_decimal`; boundary_kind `broker_server_rollover`; **preserves cycle identity, does not append new cycle**; post-sweep virtual equity resets to `seed_decimal`; checksum `1300.00 - 500.00 = 800.00` (SCN-0002) (`rollover-only-sweep.json:21-64`). Refusal `TREASURY_NO_PROFIT_TO_SWEEP` when equity ≤ seed.
- **Closed boundary (5.6):** only `{sweep, refund, re_seed}` recognized; **refund dormant** (GAP-0007), **top_up dead** (DEC-0020), **remnant_restart dead** (DEC-0023), **no automatic physical withdrawal** (`closed-treasury-boundary.json:21-79`).
- **Distinct capital concepts:** **seed S=500** (virtual), **kill-line K=200** (fixed floor), **cap C=2.5·S** (FORM-0001), **virtual equity** (`current_virtual_equity_decimal_text`, mutated by sweep), **broker equity** (Topic 13; connection-manager proof, never mutates virtual), **frozen paper balance** (Topic 7, evidence-only). Treasury virtual ledger is closed vs physical money (`closed_treasury_boundary`).

---

## Topic 13 — Stop-out (definition; breakeven-exit ambiguity; consecutive-stop-out counter B=2)

**PARTIAL.**
- **Consecutive-stop-out counter B=2 — FOUND, VERBATIM:** `scalper_breaker_threshold` symbol `B` value `2` units `consecutive_stopouts`, `"Consecutive stop-outs before bench-to-paper."` (`registry_census.json:69-80`). Feeds FORM-0004/0006.
- **Technical-kill (a different "kill"/stop concept) — FOUND (CT-BMS-03, `reconciliation-reports-and-technical-kill.json`):** report fields incl. `verdict {reconciled, drift, unknown}`, `technical_kill`, `halt_trading`, `automatic_resume_allowed` (`:50-84`; L-CODE `reconciliation.py:140-144`). Rules: `residual = broker_equity - virtual_equity - explained_delta`; `technical_kill` true **only for live-binding unexplained drift**; `automatic_resume_allowed: false` (always operator-gated). `explained_delta_parts`: `swept_but_unwithdrawn_cash, re_seed_remnant_gaps, pe_7_open_position_unrealized_pnl_open_item, paper_binding_exclusion`.
- **Stop-out DEFINITION and the breakeven-exit ambiguity — NOT FOUND.** No definition of what constitutes a "stop-out" event, and no breakeven-exit vs stop-out disambiguation, exists in this corpus (wiki/other-corpus territory).

---

## Topic 14 — Alpha-decay evidence classes; "the Book sets the bar" / qualification metrics / exam certificates / certified footprint

**FOUND (exam metrics + certificate model) / partial on "alpha-decay" wording.**
- **"The Book sets the bar" (nearest verbatim):** book-type section 3 = `entrance_exam` (`ct-book-03...json:58-59`); invariant "the book owns **admission** and sizing" (`object-lifecycle-bot.md:80`); certification is **book-specific** (`:79`).
- **Qualification / exam metrics (L-CODE `registry_census.json`, COMP-EXAM, DEC-0036), VERBATIM:**
```
WF_IS_M walk_forward_in_sample_months  = 6
WF_OOS_M walk_forward_out_of_sample_months = 1
N_OOS_MIN min_oos_trades_per_window   = 200
EV_OOS_MIN oos_expectancy_floor_r     = 0.15 R (after modeled costs)
MC_N monte_carlo_shuffle_count        = 1000
PBO_PASS_LT pbo_pass_threshold        = 0.25   (below passes)
PBO_DEAD_GT pbo_dead_threshold        = 0.50   (above is dead)
F_CHORUS chorus_expected_frequency_rule = null [GAP-0012, "Certified from cohort exam; exact threshold pending"]
```
Expectancy/break-even formulas FORM-0009/0010 (Topic 12).
- **Exam certificates / certified footprint:** `certificates_index` is a Class-1 entity with CDC (`ad-41-stream-register.json:178-195`); **trading-node certificates index is the operative validity authority**, backend `certificates_corpus` is "evidence only … presence does NOT mean validity" (`backend-postgresql-discipline.json:13,54,66-67,107-110`). Bot evidence-health shows "certificate validity and labeler parity" but "Evidence health **cannot authorize** a state transition" (`object-lifecycle-bot.md:54-63`). Exam↔live labeler parity required (`labeler-catalog-...json:64`).
- **"alpha-decay" as an explicit evidence-class taxonomy — NOT FOUND by that name** in this corpus (the decay/re-certification cascade appears as L10 recertification, `labeler-catalog-...json:368-369`, but not an "alpha-decay evidence classes" list).

---

## Topic 15 — Book/BMS validation leads (how a NEW Book or BMS proves itself before carrying money)

**FOUND (proof/ratification gates).**
- **Book/BMS write-path proof gates (L-STD):** every BMS store validates schema/trigger/foreign-key/Records-evidence **at open** and **fails closed** on drift (`treasury-...json:27`, `mode-registry-...json:28`, `book-definition-...json:34`); refusals `*_INVALID_STORED_STATE`. Book definition must validate against CT-BOOK-03 before existence (`book-definition-...json:41`).
- **NEW labeler / model admission (analogue for "prove before live", `labeler-catalog-...json:364-399`):** `new_labeler_status: requires_fresh_ratification`; `direct_live_admission_allowed: false`; `backend_shadow_output_is_authority: false`; fresh ratification required for new id/field/nature/model-family/changed-SQS; recovered models (Kronos/HMM/BOCPD/MS-GARCH) `no_current_authority` until fresh ratification + training + shadow evidence + L10 impact. Refusals `LABELER_DIRECT_LIVE_ADMISSION_REFUSED`, `LABELER_SHADOW_AUTHORITY_REFUSED`.
- **Money-carry gate:** reconciliation `ledger_reconciles_gate_ready` is "true only for fresh live-binding verdict=reconciled reports" (`reconciliation-...json:82`).
- **Paper-first before live:** birth path + warm-up→LIVE at rollover, exam-to-paper seat before LIVE (`object-lifecycle-bot.md:36-39`, `mode_registry.py:43-58`); paired-demo binding required before live routing (Topic 7).
- **Exam battery** (Topic 14) is the pre-money qualification. Preflight cold-start gate exists (`preflight-cold-start-gate.json`).

---

## Topic 16 — Same-tick priority (protective stops, Book force-flat, kill switch, fast invalidation, discretionary exits); no-overnight; hold limits; dead-zone (~45min handover)

**MOSTLY NOT FOUND — this corpus does not specify a same-tick precedence ordering.**
- **Priority/ordering that DOES exist:** the shared-account **command merge** deterministic ordering by `book_sequencer_sequence` (duplicate/missing/tie all refuse) (`paired-demo-...json:85-97`) — this orders concurrent commands on one account, but is NOT a protective-stop-vs-force-flat-vs-kill precedence table. Fill attribution requires `clientMsgId` + label (`label-based-fill-...json:17-24`).
- **Fail-closed precedence hints:** unreachable SQS = hard door block (`ct-mis-01-degradation-visibility.json:48-54`); dead feed → "downstream new entries fail closed" (`:41-47`); KSA non-overridable blockers (`flow-002:40-48`). But no ranked same-tick ordering among protective stop / Book force-flat / kill switch / fast invalidation / discretionary exit.
- **no-overnight policy / hold limits / dead-zone (~45min session-handover no-trade) — NOT FOUND.** No overnight rule, hold-time limit, or 45-minute dead-zone appears anywhere in `trading-node/`, `standards/`, or `references/`. (Only unrelated `session_boundary` **data-cleaning** policy for historical bars: `cleaning-rules-ratification.json:56-57,102`, `deep-history-...json:42,112` — that is feed hygiene, NOT a trading dead-zone.)

---

## Topic 17 — Multi-currency (account numeraire, cross-account aggregation, FX conversion for risk math)

**FOUND as explicit OUT-OF-SCOPE / unratified (L-STD `broker-equity-computation.json`, Story 4.4).**
- Broker-equity PnL is **direct-quote-currency only**; `quote_currency_must_match_balance_currency: true`; `cross_currency_conversion_in_scope: false`; refusal `CROSS_CURRENCY_CONVERSION_UNRATIFIED` (`:50-63,78`). Reconciliation residual math (Topic 13) assumes single-currency decimal text.
- Account detail (L-UI) shows per-account "balance/equity observations" and "books bound to the account" but **no cross-account aggregation or numeraire conversion** (`qmx-console-experience-architecture-v0.2.md:154-165`).
- **Account numeraire, cross-account risk aggregation, and FX conversion for risk math are NOT defined in this corpus** — cross-currency conversion is explicitly unratified.

---

## Contradictions

1. **Book birth mode: PAPER vs LIVE-ready.** L-UI `object-lifecycle-book.md:29` — "birth currently creates the book in **PAPER**"; and L-UI explicitly flags the conflict (`qmx-console-experience-architecture-v0.2.md:287-288`): "The wiki makes new books birth in PAPER; the newest direction says promoted goods arrive ready." **vs** L-STD `treasury-virtual-ledger-...json:96-98` (Story 5.4) — birth result `live_ready: true, paper_mode_created: false`. L-CODE `mode_registry.py:44` even lists `birth-in-paper` as a *relocated* (refused-here) reason marker. Layers: exploratory L-UI + wiki reference say PAPER; ratified L-STD/L-CODE say live-ready/paper-not-created. **Recorded, not adjudicated.**
2. **Promotion location.** L-UI `qmx-console-experience-architecture-v0.2.md:286` — "The wiki places promotion on Trading; the operator now places it on Agentic." Open conflict, unresolved in this corpus.
3. **"Two correlations."** `correlation_ledger` (risk-adjacent, payload OPEN — `ad-41-stream-register.json:139-157`) vs `correlation_rules` in fill attribution (label/clientMsgId matching — `label-based-fill-...json:17-24`). Same word, different mechanisms; not a true contradiction but a naming collision to flag.
4. **KSA drain.** Adapter "drain" is referenced as a real enforcement effect (`flow-002-a1-recovery.md:73`) yet `ksa_drains: false` as a non-goal of the connection-pool story (`connection-pool-...json:67`) — i.e. the effect is named in the UX model but not implemented in the ratified node build. Layer gap, not logical contradiction.

## Not-found list (checklist topics with NO / only-partial evidence in THIS corpus)

- **Topic 1 — seven doors:** referenced ("seven-door outcomes", "Doors" tab, `door_hard_block`) but **never enumerated by name**. CT-BOOK-01 schema **not found** (only CT-BOOK-02/03).
- **Topic 5 —** the specific "scalping-book-v2 = NEW Book, never inherits v1 ledger" sentence **not found** (versioning primitives present; inheritance rule inferred only).
- **Topic 6 —** SL/TP fields, dynamic/trailing stop logic, fast-invalidation, force-flat definition, "who moves the stop and when", position-safety authority: **not found** (only the ownership principle "bot owns intent; book owns admission+sizing" and adapter close_all/close_position vocabulary).
- **Topic 8 — News protection:** entirely **not found** (no windows, severity tiers, currency→instrument map, open-position policy, overrides).
- **Topic 9 —** SQS **cadence** and **hysteresis**: not found (formula/inputs/thresholds/why fully found).
- **Topic 10 —** KSA scope→effect **decision matrix** and protection logic: **deferred / non-goal** here (levels enum + operator-only de-escalation + audit stream found; matrix not implemented).
- **Topic 11 —** correlation **enforcement thresholds** and computed-vs-enforced semantics: **OPEN** (ledger stream shell only).
- **Topic 13 —** **stop-out definition** and **breakeven-exit ambiguity**: not found (only B=2 counter + technical-kill).
- **Topic 14 —** "**alpha-decay evidence classes**" as a named taxonomy: not found (exam metrics + certificate authority found; decay handled as L10 recertification).
- **Topic 16 —** same-tick precedence ordering; **no-overnight**; **hold limits**; **~45-min dead-zone / session-handover no-trade**: **not found** (only command-merge sequencing + data-cleaning session_boundary).
- **Topic 17 —** account **numeraire**, **cross-account aggregation**, **FX conversion for risk math**: present only as **explicitly unratified / out-of-scope** (single-quote-currency enforced; cross-currency conversion refused).
- **CT-BMS-04** and **CT-BOOK-01**: not found in this corpus.
