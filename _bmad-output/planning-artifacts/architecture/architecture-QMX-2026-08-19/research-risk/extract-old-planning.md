# Old-Planning Extraction — Book / BMS / Risk (GAP-0039..0046 risk sitting)

> Extractor dossier for the QMX architecture **risk sitting**. Source corpus = the OLD project generation at
> `C:/Users/Mubarak/Documents/QMX/` (READ-ONLY evidence), specifically `_bmad-output/` plus root
> `DECISIONS-LOG.md`, `TRADING-NODE-SHIP-GOAL.md`, `AGENTS.md`. All path:line citations below are relative to
> `C:/Users/Mubarak/Documents/QMX/`. This dossier **records** corpus layer + date on every load-bearing finding;
> it never rules precedence.

## Corpus-layer key (for this extractor's sources)

| Layer tag | What it is | Date | Authority note (recorded, not ruled) |
|---|---|---|---|
| **SPINE** | `_bmad-output/.../architecture-QMX-2026-07-20/ARCHITECTURE-SPINE.md` — 45 ADs, `status: final` | created 2026-07-21, updated 2026-07-23 | Old-project architecture spine (topology v2). |
| **PRD** | `_bmad-output/planning-artifacts/prds/prd-QMX-2026-07-20/prd.md` — `status: final` | created 2026-07-20, updated 2026-07-24 | Old-project PRD deterministic section. |
| **EPICS** | `_bmad-output/planning-artifacts/epics.md` — v2 rebuild | 2026-07-24 (`draft`) | Rebuilt against final spine+PRD. |
| **RES** | `.../architecture-QMX-2026-07-20/research/*-extraction.md` | 2026-07-20 | Opus subagent extractions; each line carries its own inner grade **Observed/Deduced/Proposed/Unresolved** taken from GitBook capture 2026-07-18 (authoritative), wiki/ (compiled), raw/local-cleaned (no authority). |
| **SPEC/STORY** | `_bmad-output/implementation-artifacts/spec-*.md`, `story-*` | 2026-07-26..2026-07-28 | Old-project implementation artifacts (built, self-verified). |
| **PE7-MEMO** | `.../architecture/pe-7-kill-line-position-fate-memo-2026-07-28.md` | 2026-07-28 | `status: RECOMMENDED — awaiting operator ruling`; **NOT ratification**. |
| **DEC-LOG** | root `DECISIONS-LOG.md` | 2026-08-10 | Orchestration log; self-states "NOT the wiki and never overrides it". Newest layer in this corpus. |
| **ATTIC** | `_bmad-output/attic/2026-07-22-agentic-run-reverted/**` | 2026-07-21/22 | **Reverted to attic 2026-07-22 — NO CURRENT AUTHORITY.** Flagged wherever cited. |

Note: several *verbatim* contract standards (`standards/*.json`) and the `wiki/` pages live OUTSIDE this extractor's
assigned corpus (they are repo-root dirs, not under `_bmad-output/`); where a schema's canonical bytes live there,
this dossier quotes the copy that exists inside my corpus (the extraction / spec fixture) and says so.

---

## Topic 1 — Book schema (CT-BOOK-01/02/03), versioned book-type schema, the seven doors

**CT-BOOK-01 (bot→book trade intent) — fields VERBATIM** [RES `.../research/book-template-registry-extraction.md:23`; grades: Observed]:
```
book_id, bot_id, pair, side, requested_r, footprint_version, snapshot_version, timestamp_utc
```
Field discipline [EPICS `epics.md:158` AR-24]: "CT-BOOK-01 fields exact (`requested_r` in R units, side BUY/SELL, `footprint_version`, `snapshot_version`)".

**CT-BOOK-02 (book→BMS mode state event) — fields VERBATIM** [RES `.../research/bms-extraction.md:52`]:
```
book_id, mode, reason, trigger_decision (DEC-####), effective_at_utc
```
Rules: "Paper balances freeze at mode flip"; "Breaker bench-to-paper auto-resets at next open under DEC-0032"; other transitions GAP-0006. `trigger_decision` must match `DEC-[0-9]{4}` [EPICS `epics.md:158`].

**CT-BOOK-03 = the book-type schema. MINTED by Story 5.1** (`status: done`, 2026-07-27) [SPEC `spec-5-1-ct-book-03-book-type-schema.md`]. It is ratified as a **versioned JSON-Schema contract** for book types combining template Sections 0–5, typed core columns, a ratified-keys sparse JSON bag, expression-index promotion metadata for hot attributes, registry-owned numeric authority, EAV structurally invalid, Section 6 explicitly undefined. The minimal accepted fixture (VERBATIM from the spec Design Notes, `spec-5-1...md:165-198`) — canonical bytes live in `standards/ct-book-03-book-type-schema.json` which is outside my corpus:
```json
{
  "standard_id": "CT-BOOK-03",
  "book_type_id": "book-type:governed-template",
  "book_type_version": "1.0.0",
  "template_sections": [
    {"ordinal": 0, "key": "charter"},
    {"ordinal": 1, "key": "footprint"},
    {"ordinal": 2, "key": "money_rules"},
    {"ordinal": 3, "key": "entrance_exam"},
    {"ordinal": 4, "key": "leash_chain"},
    {"ordinal": 5, "key": "capacity_and_sweep_mechanics"}
  ],
  "type_structure": {
    "grammar": "book-template-sections-0-5",
    "book_instance_creation": false,
    "book_type_specific_values_inline": false
  },
  "storage": {
    "design": "typed_core_columns_plus_sparse_ratified_keys_json_bag",
    "eav": false,
    "typed_core_columns": [{"name": "book_type_id", "type": "text", "source": "definition", "filterable": true}],
    "filtered_fields": ["book_type_id"],
    "sparse_attribute_bag": {"key_policy": "ratified_keys_only", "allowed_keys": [], "filter_authority": false, "primary_filter_surface": false},
    "hot_attribute_keys": [],
    "expression_index_promotions": []
  },
  "permitted_attribute_set": [],
  "registry_numeric_authority": {
    "inline_authoritative_values_allowed": false,
    "registry_owned_numeric_slots": [{"slot_id": "section_2_numeric_authority", "registry_ref": "registry://book-instance/{book_id}/section-2/{slot_id}", "owner_scope": "book_instance"}]
  }
}
```
Story 5.1 **acceptance criteria** [SPEC `spec-5-1...md:71-76`, all 5 pass per `story-5-1-acceptance.json`]:
1. verifier validates standard shape, validator behavior, negative refusals, CI wiring, evidence, sprint status, source constraints.
2. validator accepts a CT-BOOK-03 definition **only if** it has a stable `book_type_id`, a version, type structure, permitted attribute set, typed core columns for filtered fields, and registry references for authoritative numeric values.
3. Section-6 content / EAV / arbitrary filterable key-value / JSON-bag filter authority / inline authoritative numeric values → refuses with a specific CT-BOOK-03 schema violation.
4. storage discipline requires typed core columns for filtered fields, a sparse ratified-keys JSON bag, expression-index promotion metadata for hot attributes.
5. no book instances, mode-registry tables, Treasury tables, CT-ATTR-01, or BMS write paths claimed.

**Versioned book-type schema** also pinned architecturally [SPINE `ARCHITECTURE-SPINE.md:226` AD-26]: "A book type is a versioned JSON Schema (template grammar + type structure + attribute set); a book instance is a schema-validated JSON definition whose numerics land in the registry under instance ownership (ADR-0002). Storage: typed core columns + a sparse ratified-keys-only JSON attribute bag + expression-index promotion for hot attributes... EAV is forbidden; the JSON bag is never the primary filter surface. The scalper is one template, never the generalization; validation methods vary per book type." CT-BOOK-03 listed as a Proposed CT surface pending ratification [SPINE `:380`].

**The book template = "seven-section form"** [RES `book-template-registry-extraction.md:5`, Observed]: the corpus calls it the "seven-section form every book instantiates"; ADR-0002 **seals it as "Sections 0-5"**. Six content areas as an ordered set: charter, footprint, money rules, entrance exam, leash chain, capacity/sweep. Their bind to ordinals 0–5 is **Deduced, not printed**. Section 6 = "workspace design" = **GAP-0001, undefined; inventing forbidden** (DEC-0039).

**THE SEVEN DOORS — order (DEC-0035), VERBATIM** [RES `book-template-registry-extraction.md:22-33`; PRD `prd.md:65,172`; SPINE `:238` refs]:
```
1. Footprint          — intent conforms to measured behavior envelope; footprint_version valid (predicate NOT printed)
2. Viability veto     — round_trip_cost_R / expected_edge_R ≤ 0.10 (FORM-0007)
3. R_max              — R_max_usd ≤ B·b·Lbar (FORM-0006);  B=2, b=2, measured Lbar
4. Daily budget       — within remaining D = U/n (FORM-0003; drains intraday, re-derived at rollover); n=5
5. Breaker            — consecutive stop-outs < B; at B bench-to-paper rest of day, auto-reset next open (DEC-0032) (counter semantics NOT printed)
6. Exposure ledger    — concurrency/exposure within limits (predicate NOT printed; cross-book = GAP-0008); N_live_max=3
7. Kill switch        — KSA state permits; dead feed / SQS hard-block / news-blocked pair stop entry (DEC-0042)
```
Each refusal signs the veto ledger via CT-BMS-05 (L11/DEC-0012). Door inputs come from CT-BOOK-01, CT-MIS-01 and the registry [RES `:23`]. Acceptance predicates for doors **1 (footprint), 5 (breaker), 6 (exposure ledger)** are **NOT printed** in the corpus → ratified at Story 6.4 [EPICS `epics.md:1265-1276`]. Door 6 (exposure ledger) is explicitly NOT the BMS Exposure desk [EPICS `epics.md:158,1276`].

---

## Topic 2 — BMS schema (CT-BMS-*), what BMS owns vs what the Book owns

**BMS charter (VERBATIM)** [RES `bms-extraction.md:7`, Observed]: *"BMS accounts for and constrains books. It has Treasury, Exposure, Records, and Reporting desks, and it never trades, sizes, or reaches inside a book. DEC-0045."* **Exactly four desks**: Treasury, Exposure, Records, Reporting — no fifth desk anywhere [RES `bms-extraction.md:8`].

**BMS authority boundary** [RES `bms-extraction.md:9`]: *May* own "virtual ledger state, exposure measurement, mode registry, append-only journals, reporting metrics, KSA policy, and news block directives." *May never* "trade directly, mutate bot logic, overwrite journals in place, or bypass the veto ledger. DEC-0002, DEC-0012, DEC-0046." Authority chain: `bot → book → BMS → operator` (ADR-0001) [RES `:10`; PRD §5A].

**The five CT-BMS interfaces** [RES `bms-extraction.md:11`]:
- **CT-BMS-01** Treasury event **in** (Treasury→Records) — `event_id, book_id, cycle_id, event_type ∈ {sweep, refund, re_seed}, amount(USD), reason, occurred_at_utc`; "Only these three event types cross the book-to-treasury boundary" (DEC-0038) [RES `:60`].
- **CT-BMS-02** Mode registry **out** (BMS→KSA) — `book_id, mode ∈ {LIVE, PAPER, BENCHED, STOOD_DOWN}, updated_at_utc`; "The BMS mode registry is the authoritative mode map" (DEC-0045) [RES `:50`].
- **CT-BMS-03** Reconciliation report **in** (Treasury→BMS) — `account_id, virtual_equity, broker_equity, explained_delta, verdict ∈ {reconciled, drift, unknown}`; "Unexplained drift is a technical kill" (DEC-0015); `reconciliation_epsilon = 0 USD` [RES `:62`].
- **CT-BMS-04** News block directive **out** (BMS Exposure→KSA) — `directive_id, affected_currency, affected_pairs[], window_start_utc, window_end_utc, reason`; applies live AND paper (DEC-0010, DEC-0044) [RES `:71`].
- **CT-BMS-05** Journal append **in** (all→Records) — `journal, event_id, event_type, payload, refs, occurred_at_utc`; "Corrections append new entries that reference corrected entries" [RES `:44`].

**What BMS owns vs Book owns**:
- **BMS owns**: virtual capital ledger (Treasury), mode registry, the five append-only journals, exposure measurement, reconciliation verdicts, reporting metrics, KSA **policy**, news directives [RES `bms-extraction.md:82-85`; PRD FR-27..FR-30].
- **Book owns**: admission (seven doors), sizing (money ladder), leash chain, profile selection, roster; the Book **does not trade directly** [PRD `prd.md:62-63`; SPINE AD-1].
- **BMS→Book feed: NONE** — no contract has a BMS→Book direction; BMS emits only to KSA (CT-BMS-02/04) and feeds Notification [RES `bms-extraction.md:76`, Observed].
- Records is the **only** journal write path (CT-BMS-05; append-only; corrections reference, never overwrite) [PRD `prd.md:69`, SPINE `:114` AD-8].
- KSA is **NOT a BMS desk** — standalone `COMP-KSA`, "the global protection state machine"; BMS owns KSA policy, node enforces via adapter, bots never see KSA (DEC-0008) [RES `bms-extraction.md:68-69`].

---

## Topic 3 — Cardinalities (Book↔BMS, bot↔Book, Book↔account/venue)

- **Book ↔ BMS**: one BMS for the whole system; BMS "accounts for and constrains books" (plural). No per-book BMS. There is **no "one Book owns several BMS"** notion — BMS is singular/global, Books are many [RES `bms-extraction.md:7-10`]. **No book-registration ceremony exists** — "books simply hold the standing contract relationships"; `COMP-BOOK-TEMPLATE depends_on [COMP-EXAM, COMP-MIS-LIVE, COMP-KSA, COMP-BMS]` [RES `bms-extraction.md:77`; `book-template-registry-extraction.md:105`]. Registration/instantiation ceremony = **ABSENT / GAP-0010**.
- **bot ↔ Book**: many bots per book (a roster of seats); a bot is certified **against a specific book profile** and bound to the book profile(s) it is certified against [PRD FR-41 `prd.md:159`; DEC-0055]. Scalper: `max_concurrent_live_bots N_live_max = 3` (door-6 concurrency cap), distinct from `roster_capacity = 6 PROVISIONAL` (roster size) [SPINE `:243` AD-29; `:378`].
- **Book ↔ account / venue**: **multiple books can share ONE broker account by design** — "Treasury is a virtual ledger over a real broker account, multiple books share one account by design — and AD-30 makes account binding a free operator choice" [review-adversary `.../reviews/review-adversary.md:127`]. Reconciliation runs **per account binding** (CT-BMS-03 by `account_id`) while Treasury **ledgers are per `book_id`**, so an account's `virtual_equity` is a cross-book sum over ledgers [RES via `review-adversary.md:51`; PRD FR-26 `prd.md:318`]. Book→account-binding assignment is operator-configured via console, mutable, journaled, system-settings scope [SPINE `:250` AD-30]. Each **live** account binding pairs with a **demo** binding (two bindings per account) [SPINE `:250`; EPICS `epics.md:158`]. **May one Book bind accounts at several venues?** — Not addressed; V1 is FOREX-ONLY, single-platform (cTrader); the `(venue, platform, instrument)` dimension is carried from day one but multi-venue binding is out of V1 (future in-system venues behind their own adapters) [SPINE AD-35/AD-42 `:282-342`]. Multi-account/multi-platform load balancer deferred; "an account cannot carry many books at fleet scale" [PRD `prd.md:536`].

---

## Topic 4 — Book/BMS lifecycle states and modes; seat-state vs book-mode split

**Mode enum split (load-bearing, V1 NARROWED)**:
- **Book mode** (mode registry, CT-BMS-02): the mode-map contract enum is `{LIVE, PAPER, BENCHED, STOOD_DOWN}` [RES `bms-extraction.md:50`], **BUT V1 book map uses LIVE and PAPER only** — "no transition produces book-mode BENCHED or STOOD_DOWN; both stay reserved (KSA/A1-era semantics deferred with GAP-0015)" [SPINE `:238` AD-28; PRD `prd.md:71,292`].
- **Seat state (bot-scoped)**: **BENCHED lives at bot level as BMS-owned roster-seat state, never a V1 book mode** [PRD `prd.md:71`, `:285-286`; EPICS `epics.md:158` "BENCHED is roster-seat state, never a V1 book mode"]. Breaker bench = bot seat → BENCHED (behaving as paper) for rest of day → LIVE at next open (DEC-0032).
- **ADMITTED** is a **registration state, never a book mode** (AD-40): entered at the promote-to-live click; the unit emits no intents and holds no ledger; exits when birth + LIVE flip land atomically at the activation boundary [PRD `prd.md:95`; SPINE `:238,313` AD-28/AD-40].

**Which enum lives where**: `ksa_levels = [GREEN, YELLOW, ORANGE, RED, BLACK]` (non-configurable, DEC-0043) is KSA's, not the book's [RES `book-template-registry-extraction.md:89`]. Book mode is BMS mode-registry's. Seat state (BENCHED) is the roster/book's BMS-owned state.

**Paper transitions on the trading node = EXACTLY TWO (AD-28 v2)** [SPINE `:238`; PRD `prd.md:280-288` FR-23]:
1. **Kill-line stand-down** (book-scoped): kill line crossed → book mode PAPER until cycle-boundary `re_seed`; post-kill `re_seed` increments the cycle, never reopens cycle 1.
2. **Breaker bench + auto-reset** (bot-scoped): bot seat → BENCHED for rest of day → LIVE at next open.
All pre-live paper phases (birth-in-paper, warm-up ramp + CT-BOOK-02 flip, exam-to-paper) **relocate to the certification side**; `warm_up_days` retires from trading-node scope. GAP-0006 "RE-OPENED for this narrowed set." Everything else refuses-and-journals.

**Mode-write rule**: a mode write requires a CT-BOOK-02 report with a `DEC-[0-9]{4}` trigger decision; invalid/unratified transitions refuse and journal [EPICS `epic-5-context.md:29`]. Mode registry serves CT-BMS-02 reads (incl. to KSA) with **no mutation authority** for readers [PRD FR-28 `prd.md:334-337`].

---

## Topic 5 — Book versioning + compatibility

- **Template/instance split (ADR-0002 / DEC-0026)**: template documented once (sealed Sections 0–5); scalper documented separately as the first instance; future books reuse the grammar **without inheriting values**; values live in the registry under the owning instance [RES `book-template-registry-extraction.md:113`; PRD `prd.md:63,190-195`].
- **Book type is a versioned JSON Schema** (`book_type_id` + `book_type_version`), instances are schema-validated JSON [SPINE AD-26 `:226`; CT-BOOK-03 fixture carries `book_type_version: "1.0.0"`, Topic 1].
- Bot identity mirrors this: immutable `bot_spec_version`; "a spec revision (mutation/improvement) is a new version, parent-linked" and "certified identity is never mutated in place" [PRD FR-41 `prd.md:161-162`; SPINE AD-25]. A bot consuming a declared attribute mints a new `bot_spec_version` [EPICS `epics.md:158`].
- **"scalping-book-v2 = NEW Book, never inherits v1 ledger"**: not found as that exact phrasing. The corpus principle that supports it: money **resets between cycles while knowledge persists** (L5); the treasury virtual ledger is created at birth per book instance at seed S (CT-BMS-01 `re_seed` opening cycle 1) [SPINE AD-28; EPICS `epic-5-context.md:31`]; a new book instance instantiates with its own instance-owned registry values and its own ledger [EPICS Story 6.7 `epics.md:1308-1320`]. The explicit "a new version does not inherit the prior version's ledger" statement is **NOT-FOUND verbatim** in my corpus — see Not-found list.
- BACKWARD-compatible attribute additions auto-enter `experimental`; breaking changes forbidden in place (new version + migration + deprecation window) [SPINE `:216` AD-24].

---

## Topic 6 — Exit ownership: bots own exit organs vs Book owns exits; forced exits; fast invalidation; dynamic SL/TP; position-safety authority

- **Bots own market-facing entry/exit organs** [PRD `prd.md:61` glossary "Bot — the only market-touching actor; owns market-facing entry/exit organs"; SPINE AD-19 `:173` "Bots additionally receive the direct feed (market-facing entry/exit organs)"].
- **Post-entry position safety RULED into the book grammar (≈ template Section 4), with BMS as configuration authority** [PRD OQ-2 `prd.md:582`, `[OPERATOR-STATED]`]. But this is **ownership only**; the mechanics are unresolved (below).
- **Recovered SL/TP spec (candidate, NO ratified values)** [PRD addendum `.../prd-QMX-2026-07-20/addendum.md:71`]: "system-owned post-entry stop policy — bot supplies initial intent then relinquishes stop control; at +1R **stop moves once to spread-adjusted breakeven, never resets**; TP trails on MIS continuation probability; **KSA overrides pre-empt normal amendments**; every amendment recorded; conservative failure ('when in doubt, do not widen risk'...)." Candidate contracts: **PositionIntent, AmendInstruction (new stop/target, reason, source, priority), PipProfile**. "Thresholds have no published values."
- **Who moves stops / when — UNRESOLVED**: dynamic SL/TP requires an amend command; **CT-ADAPTER-01 has no amend** (place/cancel/close/close_all only) [RES `book-template-registry-extraction.md:108`]. Operator ruled a fifth `amend_order` command; platform capability CONFIRMED (cTrader supports SL/TP amend incl. server-side trailing) [PRD FR-31 `prd.md:358`; PE-6 `:575`]. Ratification of `amend_order` into CT-ADAPTER-01 is deferred (Story 4.2) [EPICS `epics.md:913`]. Adversarial review flags the two ruled requirements (dynamic SL/TP vs "exactly four commands") as **mutually exclusive as written** [`.../prds/.../review-adversarial-general.md:50-51`].
- **Fast invalidation vs hybrid dynamic SL/TP**: "the per-book exit-policy shape (fast invalidation primary vs hybrid with dynamic SL/TP) settles with position safety (OQ-2)" [PRD PE-6 `prd.md:575`].
- **Forced exits / hold-time force-flat**: last leash rung; "hold-time exceeded → force flat; numeric value + priority vs KSA/broker-stops/amendments **UNRESOLVED**" [RES `book-template-registry-extraction.md:47`]. See Topic 16 for the same-tick race.
- **Position fate at boundaries = PE-7, UNRESOLVED** — see Topic 16.
- Stop-policy version must pin into CT-EXAM-01 (a stop-policy change invalidates certificates as a labeler change does) — **PE-8**, deferred [PRD FR-6 `prd.md:151`, PE-8 `:577`].

---

## Topic 7 — Paper mode: bench-to-paper, paired demo bindings, duplicate-order prevention, live↔paper transitions, evidence comparability

- **Frozen counterfactual (L13)**: balance freezes at the mode flip; the book keeps sensing and paper-trading; paper gains are **never** treasury cash; paper balance is never hand-adjusted (any adjustment rejected, DEC-0014) [PRD FR-22 `prd.md:273-278`].
- **CT-PAPER-01** records the transition with the frozen balance + trigger event. Story 5.8 (`done`) is the boundary-recording owner; `standards/frozen-counterfactual-paper-semantics.json` (outside my corpus, quoted in PE7-MEMO `:67-71`): `"accepted_transition_kinds": ["kill_line_stand_down", "breaker_bench"]`, `"book_scoped_transition": {"trigger_kind": "kill_line_stand_down", "from_mode": "LIVE", "to_mode": "PAPER"}`.
- **Paired demo binding (paper = demo account, live = live account)** [PRD FR-22 `prd.md:278`, OPERATOR-STATED]: "paper trading runs on a demo trading account and live on a live trading account — a simple split at the platform API level; one book hosts both modes, only the execution binding differs." Paper/breaker-benched fills route to the book's paired demo binding [SPINE AD-30 `:250`; EPICS Story 4.6 `epics.md:971`, Story 6.10 `:1363`].
- **live↔paper transitions in V1** = the two fail-mechanism transitions only (kill-line stand-down; breaker bench+auto-reset). PAPER→LIVE only via cycle-boundary `re_seed` (kill-line) or next-open auto-reset (breaker). No birth-in-paper, no warm-up ramp on the node (AD-28 v2) [SPINE `:238`; PRD FR-23].
- **Evidence comparability / drift exclusion**: the demo binding's broker balance is *expected* to diverge from the frozen virtual balance by design and is **excluded from the live technical-kill drift check** (L14 applies to live account bindings only) [PRD FR-22 `prd.md:278`; EPICS Story 5.8 `epics.md:1145,1161`]. Architecture ruled **no separate paper-side diagnostic reconciliation in V1** (KISS): demo fills journal like all fills [PRD `prd.md:278`; SPINE Open Questions `:408`].
- **Duplicate-order prevention**: not a paper-specific mechanism; general fill de-dup is via fixed correlation keys — `clientMsgId` for command↔fill, `label` for per-bot attribution, `snapshot_version` for provenance, Records `event_id`+`refs` for lineage [SPINE AD-30 `:250`]; the AD-40 promotion pull is idempotent (keyed by artifact-reference tuple, re-pull is a no-op, "AD-44 retries can never double-admit") [SPINE `:357` / `:313`]. **News window in paper**: paper collects **NO diagnostic entry data** during a known-invalid news window (SCN-0003) [PRD FR-20 `prd.md:262`; EPICS `epics.md:74,1465`].

---

## Topic 8 — News protection: windows, severity tiers, currency→instrument mapping, open-position behavior, overrides

- **Currency→instrument mapping (VERBATIM rule)** [SPINE `ARCHITECTURE-SPINE.md:204` AD-22]: "Compilation is **currency → ALL pairs containing that currency**; session scoping may only **WIDEN** a block, never narrow it... Door 7 blocks on `affected_currency` membership of the intent's pair; `affected_pairs[]` is a non-authoritative hint." BMS Exposure owns calendar import + compile.
- **Severity tiers + before/after window widths**: "**Blocking rules (impact tiers, pre/post window widths) are DEC-linked registry variables**" [SPINE `:204`] — i.e. the tiering and window widths exist as registry variables but **their numeric values are NOT printed** in my corpus; "news-block pre/post window widths are DEC-linked registry variables (add to AR-17's slots)" [EPICS `epics-pre-v2-2026-07-24.md:148`]. Calendar impact enum is high/med/low (Forex Factory) [SPINE `:376`]. **Operator's recalled (verbal, DEC-LOG) numbers** [DEC-LOG `DECISIONS-LOG.md:36`]: "halts all trading for ~5–15 min around news; **buffer-before = buffer-after**; re-opens after the buffer; some sessions are unaffected by a given news time." (DEC-LOG layer, 2026-08-10, recalled/verbal — not a ratified registry value.)
- **Calendar source + refresh**: DAILY pre-trading-day ritual; **Forex Factory primary** (free weekly JSON, impact high/med/low, rate-limited 2 downloads/5 min), verified impact-carrying fallbacks FMP → Trading Economics → FXStreet behind one normalized import; every import journaled; failed refresh falls through the chain then degrades visibly with notification; **unknown high-impact coverage ⇒ conservative blocking** [SPINE `:204,376`; EPICS Story 7.4 `epics.md:1437-1451`]. Second, distinct acquisition pipeline from market history [RES `epics-research/data-layer-deep-read.md:33`].
- **Live AND paper**: same pair+window → same refusal class in live and paper, each signs the veto ledger (L9, SCN-0003) [PRD FR-20; EPICS `epics.md:1453-1465`].
- **Open-position behavior during news / overrides**: **NOT specified** — the corpus defines news as a **door-7 entry block** ("stop entry"); it does not state what happens to an already-open position during a news window, and there is no operator override path (news blocks are non-discretionary, L3/L9). Open-position fate at any boundary is PE-7 (Topic 16). Session scoping can only widen, never narrow — no narrowing override [SPINE `:204`].

---

## Topic 9 — SQS / spread-quality sensing: formula, inputs, thresholds, cadence, hysteresis, and WHY

- **SQS = "snapshot quality score"** (NOT "spread-quality"). "an unreachable SQS forces a hard door block" [RES `epics-research/mis-models-deep-read.md:34,46`, Observed; PRD glossary `prd.md:78`].
- **Original formula/inputs = UNDOCUMENTED in the authoritative source** [RES `mis-models-deep-read.md:46`, Unresolved]: "the acronym is never expanded in the ratified source with a formula; **inputs and computation are undocumented**" (cites `.../research/mis-data-flow-extraction.md:63-67`).
- **RATIFIED by Story 3.1** (`done`, 2026-07-26) as **`sqs_weighted_component_floor_v1`** [STORY `story-3-1-progress.md:16`]: "computed with **integer basis-point component qualities and weights**. The proof returns deterministic **Decimal** score evidence plus the exact inputs used." A **minimum reachable score floor** is in the SQS contract; reachable scores below it are refused; **unreachable SQS → `sqs_hard_block: true`** [SPEC `spec-3-1...md:92,96`]. Design intent: "a deterministic composition of named component qualities so later runtime code can implement it exactly; threshold values must be catalog parameters or unresolved evidence, not hidden defaults" [SPEC `spec-3-1...md:134`]. The **exact weight/threshold values live in `standards/labeler-catalog-ratification.json`** (outside my corpus). One weight fact recalled: **`regime_classifier_v1` feeds 10% of SQS** [DEC-LOG `DECISIONS-LOG.md:44`, DEC-LOG layer]. A `ratification_evidence` block records that AR-21 SQS weights were unresolved before Story 3.1 and that Story 3.1 is the ratification act [SPEC `spec-3-1...md:111`; STORY `story-3-1-progress.md:59`].
- **Cadence**: SQS is a labeler emitted per snapshot (once per labeler/params/pair/resolution, fanned out — DEC-0041) [SPINE AD-19]; carried as `sqs_score` + `sqs_hard_block` fields of every CT-MIS-01 snapshot [SPEC `spec-3-3...md:28`].
- **Hysteresis**: **NOT-FOUND** — no hysteresis mechanism for SQS anywhere in my corpus.
- **WHY it existed**: to gate door 7 — "SQS-unreachable = hard door block" (DEC-0042); MIS is information-only (L6), so SQS surfaces quality/degradation evidence and the **book's door 7** enforces the hard block [RES `book-template-registry-extraction.md:33,106`; PRD FR-17 `prd.md:239`].

---

## Topic 10 — Kill switch / KSA: authority model, scopes, escalate-only, effect vocabulary, adapter interaction

- **Authority model**: KSA = standalone `COMP-KSA`, "the global protection state machine" — levels `GREEN, YELLOW, ORANGE, RED, BLACK` (non-configurable, DEC-0043), trigger classes `scheduled_news, black_swan, connectivity, unknown_state` (CT-KSA-01) [RES `bms-extraction.md:68`; PRD `prd.md:79` FR-19]. **BMS owns KSA policy, the trading node enforces effects through the adapter, and bots never see KSA directly (DEC-0008, L7)** [RES `bms-extraction.md:69`; SPINE AD-21 `:199`].
- **Escalate-only + human de-escalates (L8)**: "Automated transitions escalate only; de-escalation is A1 human authority alone." No automated path from higher to lower level (structural — Story 7.2 fixture rejects automated de-escalation); DEC-0019's TIGHTEN half-size level is **dead** and must not reappear [PRD FR-19 `prd.md:252-254`; EPICS `epics.md:1421`]. A1 resurrection is the sole human de-escalation power, not schedule-bound [PRD `prd.md:80`; EPICS Story 7.9 `epics.md:1509-1522`].
- **Scopes** (recorded, layered):
  - **Global**: KSA state machine is global protection state [PRD `prd.md:79`].
  - **Account**: a KSA transition **quiesces and drains ALL of an account's connections** before enforcement counts complete (AD-23) [SPINE `:209`; EPICS Story 7.3].
  - **Pair/currency**: news directives block by `affected_currency`/affected pairs (CT-BMS-04) [Topic 8].
  - **Book-level**: leash-chain rung "classed kill switch" + kill-line stand-down are book-scoped; DEC-LOG recalls "**Book-level kill switches: originate from the BMS, depend on the book; require correlation analysis**" [DEC-LOG `DECISIONS-LOG.md:38`, recalled].
  - **Venue**: not present (FOREX-ONLY V1).
- **Effect vocabulary**: at the adapter, effect = "**block / close per the ratified mapping**" [EPICS Story 7.7 `epics.md:1491`]; `close_all` is a CT-ADAPTER-01 command guarded by the drain barrier so "no queued order lands after a `close_all`, ever" [SPINE AD-23 `:208`; EPICS Story 7.3]. **The full trigger→level→effect matrix = GAP-0015, fail-closed meanwhile** (unknown state blocks; no invented level) — PE-5, ratified minimally at Story 7.1 for the scalper (ENH-0008 YELLOW/RED candidate, proposed-not-ratified) [SPINE `:387`; PRD FR-21/PE-5 `prd.md:264,574`; EPICS Story 7.1 `epics.md:1396-1408`]. A ratified per-level "suspend-new vs drain vs close_all" effect vocabulary is **NOT printed** (rides GAP-0015).
- **Adapter interaction**: KSA effects enforced **only at the adapter boundary** — "the only place protection touches the market path" (FR-33/L7). A KSA transition completes only after sequencer quiesce + full connection drain (AD-23) [PRD FR-33 `prd.md:366`; SPINE AD-21/AD-23].
- **Black-swan**: "manually triggered" [DEC-LOG `DECISIONS-LOG.md:37`, recalled]. Primary kill-switch source per operator = `Documents/Claude/QMX-discussion` (Epic 7, separate session) [DEC-LOG `:39`].

---

## Topic 11 — Correlation ledger / correlation rules: computed vs enforced

- **Correlation ledger (single-line definition, VERBATIM)** [RES `bms-extraction.md:24`, Observed]: Required Journals register row `| Correlation ledger | COMP-BMS | Chorus observations and cohort references |`. **This is the ONLY definition in the corpus — no dedicated contract, no field schema, no named reader.** Owner `COMP-BMS`; writer = BMS Records via CT-BMS-05; ships **writer-only** (no reader, no invented schema) [RES `bms-extraction.md:25-26`; EPICS `epics-pre-v2-2026-07-24.md:148`].
- **Computed**: cohort correlation is measured at exam → **CT-EXAM-02** (Exam→Book) fields `cohort_id, book_id, correlation_observations, expected_loss_shape, certified_at_utc`; rule "**Chorus thresholds derive from cohort exam observations**" [RES `bms-extraction.md:27`]. The **chorus flag** (leash rung) is an "automatic listener for abnormal loss shape... owns rate and clustering shape, not amount lost" (DEC-0048) [RES `bms-extraction.md:28`].
- **Enforced**: the chorus-flag leash rung listens for abnormal loss-shape rate/clustering — but its threshold `chorus_expected_frequency_rule (F_CHORUS) = null` → **GAP-0012**, so the rung is **reachable but inert (never fires)** in V1; no invented threshold [RES `bms-extraction.md:28`; EPICS Story 6.8 `epics.md:1334`]. Human correlation/dedup judgment is enforced at the **promotion evidence panel** (AD-27) — certificate summary, cohort-correlation observations, pair/session overlap, spec/footprint similarity — recomputed against the FRESH local roster at click time [SPINE `:233` AD-27].
- **Cross-book exposure cap authority (Exposure desk v2) = GAP-0008, NOT enforced in V1** [RES `bms-extraction.md:17`; `book-template-registry-extraction.md:32`].

---

## Topic 12 — Money ladder + R: FORM-0004 / FORM-0006, variable meanings + units, seat/offer/take, treasury seed-to-cap + sweep, distinct capital concepts

**The money-ladder formulas (VERBATIM, FORM-0001..0010)** [RES `book-template-registry-extraction.md:53-62`; PRD FR-2/FR-10; EPICS `wiki-completeness-sweep.md:151`]:
```
FORM-0001 cap_equity:        C = cap_multiple × S            (rollover check only)
FORM-0002 runway:            U = E − K
FORM-0003 daily_loss_budget: D = U / n                       (re-derived at rollover, drains intraday)
FORM-0004 offer_per_seat:    offer_R_usd = D / (B × b × Lbar)
FORM-0005 take_per_seat:     take_R_usd  = min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)
FORM-0006 r_max_ceiling:     R_max_usd ≤ B × b × Lbar
FORM-0007 viability_floor:   round_trip_cost_R / expected_edge_R ≤ v_cost
FORM-0008 refund_reserve:    reserve ≈ rho × N_cycles_month × S     (GAP-0007; approximate)
FORM-0009 expectancy:        EV = p·W − (1−p)·L − c        ("never from winning-trade anatomy alone")
FORM-0010 break_even:        p > (L + c) / (W + L)
```
**Variable meanings + units** [RES `book-template-registry-extraction.md:64-92`; addendum `:40`]:
- **S** = `scalper_seed_capital` = 500 **USD** (configurable; S > K; operator-countersigned default, DEC-0029).
- **K** = `scalper_kill_line` = 200 **USD** (configurable **between** cycles; **fixed WITHIN a cycle**).
- **E** = current book equity state (USD) — its intraday composition (does it include unrealized PnL?) is **unstated** [PE7-MEMO `:189-190`].
- **U** = runway (USD) = E − K.
- **D** = daily loss budget (USD) = U / n; drains intraday, re-derived at rollover.
- **n** = `scalper_runway_divisor` = 5 (dimensionless; "floor-trader discipline number").
- **B** = `scalper_breaker_threshold` = 2 **consecutive stop-outs** (dimensionless count).
- **b** = `scalper_budget_shaping_factor` = 2 (dimensionless).
- **Lbar** = `scalper_mean_loss_r` = **measured per bot at exam**; **kind: measured, configurable:false**; reference_expectation 0.35R (reference only, never an inherited default). Units: **R**.
- **cap_multiple** = 2.5; **v_cost** = `viability_cost_fraction_max` = 0.10; **rho**, **N_cycles_month** = null (GAP-0007).
- **offer_R_usd / take_R_usd** = per-seat offer/take (the terminal sizing number).

**UNIT AMBIGUITY (recorded, unresolved)**: FORM-0006 writes `R_max_usd ≤ B × b × Lbar`; the RHS `B·b·Lbar = 2·2·0.35R = 1.4R` is in **R**, while the LHS is named `_usd`. Same mixed-units issue in FORM-0004 `offer_R_usd = D(usd)/(B·b·Lbar(R))`. The corpus does not reconcile the R↔USD unit bridge; recorded here, not ruled. See Contradictions.

**Seat / offer / take mechanics** [RES `:57`; PRD FR-10 `prd.md:184-188`]: chain (DEC-0030) equity → runway → daily loss budget → offer per seat → take. "**The book offers; trust-bounded cost-aware Kelly disposes**." Kelly implementation = bot/book responsibility, NOT a registry number. FORM-0005's `trust_bounded_cost_aware_kelly` term is **not registered → PE-4, blocks live sizing**; `take` stays visibly incomputable, never defaulted to `offer` [PRD `prd.md:188`; SPINE `:395`; EPICS Story 6.6 `epics.md:1305`]. SCN-0001 checksums recompute: S=500, K=200, n=5 → U=300, D=60 (offer/take not reached) [PRD FR-1 `prd.md:114`].

**Treasury seed-to-cap + sweep** [RES `bms-extraction.md:61`; PRD FR-24 `prd.md:300-304`]: cycle = seed→cap; compound within, ratchet between; cap C = cap_multiple×S checked at **rollover only**; **sweep = rollover-only** (equity above seed), then reset virtual equity to seed; cap-hit intraday → complete the day, sweep at rollover (SCN-0001/0002; E=1300 at rollover, S=500 → sweep 800, post-sweep 500). Only sweep/refund/re_seed cross the boundary (DEC-0038). Birth creates the virtual ledger at S, emits `re_seed` opening cycle 1 [EPICS `epic-5-context.md:31`].

**Distinct capital concepts** [PRD `prd.md:571` PE-2]: "the **virtual ledger** is deliberately a distinct concept from the **broker balance**." Also distinct: seed (cycle start), cap (cycle ceiling), kill line (floor→paper), runway (E−K), daily loss budget (U/n), swept-but-unwithdrawn cash, remnant (post-kill capital, diagnostic/accounting only, DEC-0023). No automatic physical withdrawals — sweeps are virtual accounting [PRD `prd.md:507`].

---

## Topic 13 — Stop-out: definition, breakeven-exit ambiguity, consecutive-stop-out counter B=2

- **"Stop-out" has NO ratified classification** [PRD FR-14 `prd.md:219`, PE-3 `:572`]: "does a breakeven exit count? a KSA-forced flat?" — it gates the breaker AND, via `B` in FORM-0004/0006, **seat sizing**. This is **PE-3, a pre-epic blocker**, ratified at **Story 6.1** [SPINE `:386`; EPICS `epics.md:1224-1235`].
- **Breakeven-exit ambiguity (the crux)** [RES via `.../prds/.../review-adversarial-general.md:69-71`]: the recovered SL/TP rule moves the stop to breakeven at +1R; "OQ-2 explicitly leaves open whether a **breakeven-stop exit** counts" toward the breaker. "`B = 2` is a direct input to FORM-0004 and FORM-0006, so the stop-out taxonomy flows straight into position sizing. An open definition sits under both the only ratified automatic protection transition and the money ladder."
- **Story 6.1 ratification scope** [EPICS `epics.md:1234`]: "every exit type (natural stop, **breakeven exit, KSA-forced flat**, manual-equivalent close) is explicitly classified as counting or not counting toward the breaker" and the taxonomy must stay **projection-computable** (AD-9) — rebuildable from `trade_journal` + `book_journal` + registry.
- **Consecutive-stop-out counter B=2**: `scalper_breaker_threshold B = 2 consecutive_stopouts` [RES `book-template-registry-extraction.md:70`]. At B consecutive stop-outs → bench-to-paper for rest of day, auto-reset next open (DEC-0032). The **counter must survive a crash** — protection-state projection (breaker counters, drained budget D, exposure) rebuilt from journals before intents accepted (AD-9, fifth readiness gate); adversarial finding: without it, "stop-out #1 journaled; crash; restart; breaker counter = 0; stop-out #2 doesn't bench" [SPINE `:116` AD-9; RES `adversarial-coherence-attack.md:28`]. The breaker **counter semantics** (what resets it, exactly when) are **NOT printed** — deferred to Story 6.1/6.4 [RES `book-template-registry-extraction.md:31`; `fine-grain-sweep.md:67`].

---

## Topic 14 — Alpha-decay evidence classes; "the Book sets the bar" / qualification metrics / exam certificates / certified footprint

- **Exam is always against a specific book profile** ("the Book sets the bar"): "the Examination Engine certifies a bot **against a specific book's profile** — never in the abstract" (DEC-0055); the certificate is **evidence, not authorization** — the book's **entrance-exam door decides admission** [PRD §4.2 `prd.md:131`, FR-7 `:153-156`; RES `book-template-registry-extraction.md:14`]. The exact phrase "the Book sets the bar" is not in my corpus verbatim; the concept is fully present.
- **Two exam gates**: "the edge is real after costs, and the candidate is not fiction (anti-overfitting)" (DEC-0036) [PRD `prd.md:131`; RES `:14`].
- **Qualification metrics / battery (VERBATIM)** [RES `book-template-registry-extraction.md:14,78-84`; PRD FR-5 `prd.md:140`]: walk-forward **6mo IS / 1mo OOS**, **≥200 OOS trades/window**, **≥0.15R OOS expectancy after modeled costs**, **1000 Monte Carlo shuffles**, **PBO pass < 0.25 / dead > 0.50**. A window with <200 OOS trades does not count.
- **Exam certificate CT-EXAM-01 (fields VERBATIM)** [RES `book-template-registry-extraction.md:14`; PRD `prd.md:89,146`]: `labeler_versions, ev_by_regime, mean_loss_r (Lbar), fire_rate_band, breaker_expectation, cost_ratio`. **CT-EXAM-02** (cohort correlation cert): `cohort_id, book_id, correlation_observations, expected_loss_shape, certified_at_utc`. Measured Lbar feeds seat pricing (FORM-0004/0006) as a per-bot measurement, never a default.
- **Certified footprint**: the footprint is "a bot's measured behavior envelope... measured in exam and live journals, **not accepted from bot self-description**" (DEC-0035); carries `footprint_version` [PRD `prd.md:88`; RES `book-template-registry-extraction.md:12`]. Door 1 checks footprint conformance.
- **Parity (L10)**: a certificate whose labeler versions differ from live labeler versions is **void**; the bot must re-certify before live; any labeler-version change forces re-certification [PRD FR-6 `prd.md:148-149`].
- **Alpha-decay evidence classes**: **decay math was NEVER written down** — **OQ-14, WF3 home**, "expected months after the system is live — a future update, not V1 work; any ratified version must be registry/formula-owned" [PRD OQ-14 `prd.md:598`; SPINE `:389` "Decay math (OQ-14) — WF3 home; formulas were never written down"]. **Analytics non-authority (§5B)**: performance/decay evidence flows to Sunday review / sunset review / agentic analysis — **never to sizing, allocation, or mode changes** [PRD `prd.md:471`; SPINE `:285`]. Richer decay-monitoring machinery (hypothesis register `raw→...→decayed|killed`, decay monitor = evidence+notification, DPR/PRS) exists **only in the ATTIC (reverted agentic run, NO AUTHORITY)** [ATTIC `.../architecture-QMX-agentic-2026-07-21/ARCHITECTURE-SPINE.md:190,339`] — flagged, not authority.

---

## Topic 15 — Book/BMS validation leads: how a NEW Book or BMS proves itself before carrying money

- **Multi-book structural proof (SM-5)**: V1 must **structurally prove** multi-book capability — a second book instance with a **materially different profile** (different door config + money-shape values; prop-firm-shaped, not a near-clone) instantiates and passes door/sizing tests **without any change to global infrastructure** [PRD SM-5 `prd.md:554`, FR-11 `:195`; EPICS Story 6.7 `epics.md:1308-1320`]. A fixture diffs global infra code paths before/after and confirms zero modification; a disabled capability leaves a dormant socket (L2).
- **Validation methods vary per book type** [SPINE AD-26 `:226`]: "validation methods vary per book type"; "the scalper is one template, never the generalization."
- **A NEW bot proves itself** via the exam battery against the target book profile (Topic 14) + the promotion gate (AD-27): schema conformance → precondition verification (config validity, parity checks, verified paired demo binding) → any failure refuses-and-journals → human promotion click with evidence panel [SPINE `:233` AD-27]. **ADMITTED** state carries no trading authority until birth + LIVE at the activation boundary [SPINE AD-28/AD-40].
- **Certification-side is "the airport, never the planes"** — the deterministic side builds only the consuming surfaces (schema intake, certificates, seats/roster, paper routing, promotion click); WF2 (backtest→paper) is agentic-driven and ENDS at paper-complete [SPINE `:285` AD-35]. SM-6: overfit archetypes fail the battery while a known-good control passes; a mismatched-labeler certificate blocks live [PRD SM-6 `prd.md:555`].
- **BMS non-authority is validated deliberately** (Story 5.12): an undocumented desk-authority request refuses, preserving GAP-0010 [EPICS Story 5.12 `epics.md:1191`; PRD FR-30].
- **`reconciliation_epsilon = 0`** with mandatory operator review before any non-zero — the drift bar a book's ledger must clear to carry money [RES `book-template-registry-extraction.md:76`; PRD FR-3/FR-26].

---

## Topic 16 — Same-tick priority; no-overnight; hold limits; dead-zone

- **The same-tick close-authority race is UNRESOLVED** — direct quote via PE7-MEMO `:292` (from `wiki/topics/position-safety-and-sltp-authority.md:49`, wiki layer, outside my corpus): *"KSA effects, hold-time force-flat, broker-side stops, and normal amendments can collide on the same tick; **no current priority contract resolves that race**."* Listed as deferred close-priority ordering (KSA effects vs hold-time force-flat vs broker hard stops vs amendments) [RES `.../reviews/review-gap-sweep.md:57`; brief addendum `:79`]. Recovered SL/TP spec asserts only "KSA overrides pre-empt normal amendments" [PRD addendum `:71`] — a partial ordering, not the full contract.
- **Leash-chain order (VERBATIM, DEC-0037)** [RES `book-template-registry-extraction.md:37`; PRD FR-12 `prd.md:198`]: `ambient governor → day closure → bench-to-paper → chorus flag → kill-line stand-down → classed kill switch → hold-time force-flat`. PE7-MEMO notes the corpus "names **hold-time force-flat as a distinct, strictly later rung than kill-line stand-down**" — reading forced flattening as a more severe, later act than the stand-down [PE7-MEMO `:286`].
- **Position fate at boundaries (PE-7) — UNRESOLVED**: flatten vs carry at **rollover / sweep / re-seed / kill-line / paper flip**, and whether unrealized PnL enters the sweep [PRD PE-7 `prd.md:576`; SPINE `:386`]. Ratified at **Story 6.2**; each boundary type must state explicitly flatten-or-carry and how unrealized PnL enters Story 5.5 sweep + Story 5.9 `explained_delta` [EPICS `epics.md:1237-1248`]. **PE7-MEMO (2026-07-28, RECOMMENDED, NOT ratified)**: recommends Story 5.7 built PE-7-neutral (mode flip only, no position action); architect's **lean = flatten at the kill-line specifically, carry elsewhere** — offered as recommendation only, with FR-12 leash ordering flagged as genuine counter-evidence [PE7-MEMO `:254-305`]. Interlock: any open position forces reconciliation verdict `unknown` → `ledger_reconciles_gate_ready` false → FR-32 blocked [PE7-MEMO `:86-112`, quoting `reconciliation.py:387-412`].
- **`explained_delta` decomposes into EXACTLY FOUR journaled parts**: cumulative swept-but-unwithdrawn cash, re-seed remnant gaps, **open-position unrealized PnL (PE-7-gated — carried as an explicit open item, never invented)**, and the paper-binding exclusion [EPICS Story 5.9 `epics.md:1158-1161`; PRD FR-26 `prd.md:317`].
- **Hold limits / no-overnight**: the **hold-time force-flat** rung exists ("hold-time exceeded → force flat") but its **numeric value + priority are UNRESOLVED / NOT printed** [RES `book-template-registry-extraction.md:47,123`; `fine-grain-sweep.md:67`]. A **no-overnight policy** as such is **NOT-FOUND** — only the hold-time force-flat rung; no explicit "positions must be flat overnight" rule in my corpus.
- **Dead-zone (~45min session-handover no-trade): NOT-FOUND** — no dead-zone / session-handover no-trade window anywhere in my corpus. (Sessions are informational-only, may only WIDEN a news block, never authority — DEC-0025 [SPINE AD-22 `:204`]; the exact PE-1 rollover session definition is pending operator ruling, values null [SPINE `:406`].)

---

## Topic 17 — Multi-currency: account numeraire, cross-account aggregation, FX conversion for risk math

- **Account numeraire / base currency / FX conversion: essentially NOT-FOUND.** No `numeraire`, `account_currency`, `base currency`, or FX-conversion design exists anywhere in my corpus (exhaustive grep). Registry money values are stated in **USD** (S=500 USD, K=200 USD, CT-BMS-01 `amount(USD)`), and money arithmetic is exact (platform-scaled integers at the boundary, Decimal for derived math; binary float banned on money/equity/sizing paths — AD-39) [SPINE `:306-309`; RES `book-template-registry-extraction.md:66-67`], but **no rule converts a non-USD broker account to the USD registry numeraire**.
- **Cross-account / cross-book aggregation (the one adjacent fact)**: CT-BMS-03 reconciles **per `account_id`**, while Treasury ledgers are **per `book_id`**, so an account's `virtual_equity` is a **cross-book sum over ledgers, computed on the trading node** (control-path projection, AD-7 exemption) [RES via `.../reviews/review-adversary.md:51`; SPINE AD-7 `:107`]. This is book→account aggregation within one numeraire, **not** cross-currency FX.
- **`(venue, platform, instrument)` dimension** carried in every instrument-scoped schema/key from day one (FOREX-ONLY values at V1) [SPINE AD-42 `:339`] — this is the venue/instrument axis, not an account-numeraire/FX axis.
- Broker-equity computation is connection-manager-side (Story 4.4) feeding CT-BMS-03 [EPICS Story 4.4 `epics.md:943`; `epic-5-context.md`]; whether it normalizes currency is **not stated**.

---

## Epic map (which epics existed + scope) and the risk-touching stories

**Epics (v2 rebuild, `epics.md:257-331`; DEC-LOG notes old project "reached epic 6 of 8 with stories in development", but the v2 doc enumerates 10 epics):**
1. Foundation — numbers/evidence trustworthy (`:333`)
2. Data acquisition — market history (`:646`)
3. MIS — the system senses the market (`:762`)
4. Execution boundary — commands reach the market (`:896`)
5. **BMS & Treasury — books exist and money governs** (`:1000`)
6. **Doors & sizing — books govern trades** (`:1222`)
7. **KSA & protection — the machine protects itself** (`:1394`)
8. QML — the bot-authoring library (`:1539`)
9. Admission, activation & notifications (`:1638`)
10. Operator console — contract surfaces, NO UI build (`:1794`)

**Sprint reality** [DEC-LOG `DECISIONS-LOG.md:6-10`; `sprint-status.yaml` via PE7-MEMO]: Epics 1–3 stories largely `done`; Epic 5 stories **5.1–5.6, 5.8, 5.9 done**, **5.7 backlog** (PE-7 escalation, resolved by PE7-MEMO to build PE-7-neutral); **4.1–4.3 backlog**; 3.8/3.9/5.7/5.10/5.11/5.12/5.13 parked/backfill.

**Every Book/BMS/risk/exits/paper/news/kill-switch story (epics.md + specs):**
- **5.1** CT-BOOK-03 book-type schema (`done`) — Topic 1. AC in Topic 1.
- **5.2** Book definition — minimal existence (`done`) `:1016`.
- **5.3** Mode registry — authoritative book-mode map (`done`) `:1029` — LIVE/PAPER only, CT-BOOK-02 write w/ DEC trigger.
- **5.4** Treasury virtual ledger + birth mechanics (`done`) `:1043` — ledger at S, `re_seed` opens cycle 1.
- **5.5** Rollover-only sweep (`done`) `:1058` — consumes caller-supplied `rollover_equity_decimal`, PE-7-neutral.
- **5.6** Closed Treasury boundary (`done`) `:1072` — only sweep/refund/re_seed; refund dormant refuses.
- **5.7** Kill-line stand-down (backlog→PE-7-neutral) `:1087` — Topics 4/16; PE7-MEMO 7 deliverables.
- **5.8** Frozen counterfactual paper (CT-PAPER-01) (`done`) `:1132` — Topic 7; wires demo-binding drift exclusion flag.
- **5.9** Reconciliation + technical kill (`done`) `:1148` — Topic 16; four-part `explained_delta`.
- **5.10** Missed-rollover catch-up `:1164` — shares Story 5.9 projection.
- **5.11** Powerless Reporting (backend) `:1177`; **5.12** BMS non-authority enforcement `:1191`; **5.13** Prometheus/Grafana metrics `:1205`.
- **6.1** PE-3 stop-out taxonomy `:1224` — Topic 13. **6.2** PE-7 position fate `:1237` — Topic 16.
- **6.3** Attribute register + CT-ATTR-01 `:1250`. **6.4** Door predicates (footprint/breaker/exposure) `:1265` — Topic 1.
- **6.5** Seven ordered doors + veto-ledger signing `:1278` (door 7 fail-closed stub). **6.6** Money ladder (offer complete, take unbound) `:1293` — Topic 12.
- **6.7** Template/instance + second-instance proof `:1308` — Topic 15. **6.8** Leash chain `:1322` — Topics 11/16.
- **6.9** Book non-authority `:1336`. **6.10** Scalper profile + breaker bench `:1350` — Topics 4/13.
- **6.11** Profile boundary discipline `:1365`. **6.12** Bot identity + protection-state projection (5th gate) `:1378` — Topic 13.
- **7.1** PE-5 KSA trigger→level matrix `:1396` — Topic 10. **7.2** KSA escalate-only core `:1410`. **7.3** KSA quiesce/drain barrier `:1424`.
- **7.4** News compilation `:1437` — Topic 8. **7.5** Global news blocks live+paper `:1453` — Topic 8. **7.6** Unknown state fails closed `:1467`.
- **7.7** KSA effects at adapter — door 7 goes live `:1480` — Topic 10. **7.8** Supervision/fail-closed stand-down `:1495`. **7.9** A1 resurrection `:1509`. **7.10** Fault-injection (SM-7) `:1524`.

**PRD risk sections**: §4.3 Book Template & Multi-Book (FR-8..13), §4.4 Scalper (FR-14..15), §4.6 KSA & News (FR-19..21), §4.7 Paper (FR-22..23), §4.8 Treasury & Cycle (FR-24..26), §4.9 BMS Records/Reporting/Mode/Exposure (FR-27..30), §5A Constitution L1..L17, §5C Safety posture, §10 PE-2..PE-8/OQ-2 [PRD `prd.md:167-348,421-479,563-599`].

**DECISIONS-LOG relevant** [DEC-LOG `DECISIONS-LOG.md`]: kill-switch = GAP-0015, adapter fails closed, numeric matrix in Epic 7, separate session (`:33`); recalled kill-switch context — news 5–15 min buffer-before=buffer-after, black-swan manual, book-level from BMS + correlation, primary source `Documents/Claude/QMX-discussion` (`:34-39`); 4-2 below-minimum-stop-distance is NOT a clamp — the BOOK governs all money/risk/sizing, read from GitBook, prefer oldest (`:40`).

---

## Contradictions

1. **R vs USD units in FORM-0004/0006** — `offer_R_usd = D(usd)/(B·b·Lbar(R))` and `R_max_usd ≤ B·b·Lbar` name USD outputs but the RHS `B·b·Lbar` evaluates in R (2·2·0.35R = 1.4R). The corpus never bridges R↔USD. [RES `book-template-registry-extraction.md:56,58`; PRD FR-10.] Unresolved.
2. **Dynamic SL/TP vs "exactly four adapter commands"** — OQ-2 rules dynamic post-entry stops into the book grammar (needs an amend), but CT-ADAPTER-01 hard-caps at place/cancel/close/close_all. Flagged "mutually exclusive as written"; resolution = ratify a fifth `amend_order` (Story 4.2, pending). [PRD review `.../review-adversarial-general.md:50-51`; PRD FR-31/PE-6.]
3. **PE-7 gate text vs merged practice** — `sprint-status.yaml`/`epics.md:147` (AR-16) say PE-7 "blocks Treasury/book-boundary stories (Epic 5)", yet Stories 5.4/5.5/5.6/5.9 merged through it PE-7-neutral. PE7-MEMO reads the gate text as imprecise and recommends amending it; warns the alternative reading "invalidates four merged stories". Not operator-confirmed. [PE7-MEMO `:464-468`.]
4. **Kill-line: flatten vs carry** — genuine internal tension: L16 + DEC-0023 (remnant diagnostic-only) pull toward FLATTEN; L12 + the leash order (hold-time force-flat is a strictly LATER, more severe rung than kill-line stand-down) pull toward CARRY. Corpus does not decide; PE7-MEMO leans flatten-at-kill-line-only but flags the counter-evidence. [PE7-MEMO `:267-305`.]
5. **CT-MIS-02 and CT-BMS-03 producer/consumer direction** — flagged as an unreconciled wiki documentation defect (OQ-13). [PRD `prd.md:245,320,597`.]
6. **Recovered registry-as-journal-writer vs Records-sole-writer** — recovered design has a second journal writer; conflicts with FR-27/DEC-0046; recovered model is dead unless ratified. [RES `bms-extraction.md:86`; PRD `prd.md:332`.]
7. **AD-7 "all aggregation on backend" vs trading-node control-path aggregation** — reconciliation's cross-book per-account virtual-equity sum + breaker/stop-out counters must aggregate ON the trading node (AD-9/AD-10 control path), which the absolute reading of AD-7 would ban; resolved by AD-7's control-path carve-out but noted as a near-contradiction. [RES `.../reviews/review-adversary.md:51`; SPINE AD-7 `:107`.]

---

## Not-found (checklist topics with no evidence in THIS extractor's corpus)

- **Topic 9 — SQS exact formula/weights/thresholds VERBATIM**: only the ratified NAME (`sqs_weighted_component_floor_v1`), structure (integer-basis-point weighted components + minimum-reachable floor + unreachable→hard-block), and one recalled weight (regime = 10%) are in my corpus; the exact weight/threshold numbers live in `standards/labeler-catalog-ratification.json` (outside my corpus). **SQS hysteresis: entirely NOT-FOUND.**
- **Topic 8 — News before/after window widths (minutes) and severity-tier numeric values**: exist only as "DEC-linked registry variables" with **values not printed**; the only minutes figure is the operator's recalled "~5–15 min, buffer-before=buffer-after" (DEC-LOG, verbal). **Open-position behavior during a news window and news overrides: NOT specified.**
- **Topic 16 — Dead-zone (~45min session-handover no-trade): NOT-FOUND.** No-overnight policy as an explicit rule: NOT-FOUND (only the hold-time force-flat rung, value unresolved). Same-tick priority contract: explicitly UNRESOLVED (not merely absent).
- **Topic 17 — Account numeraire / base-currency / FX-conversion for risk math: NOT-FOUND** (money is USD-denominated with exact arithmetic; no cross-currency conversion rule; only book→account single-numeraire aggregation exists).
- **Topic 5 — "scalping-book-v2 = NEW Book, never inherits v1 ledger" verbatim: NOT-FOUND** (the supporting principles — versioned schema, per-instance ledger at birth, L5 money-resets-knowledge-persists — are present, but the explicit non-inheritance-of-prior-ledger statement is not).
- **Topic 10 — Full KSA trigger→level→effect matrix and per-level effect vocabulary (suspend-new/drain/close_all mapping): NOT-FOUND** — GAP-0015, fail-closed; only "block/close per ratified mapping" + the drain barrier are stated; the scalper YELLOW/RED mapping (ENH-0008) is proposed-not-ratified.
- **Topic 11 — Correlation-ledger field schema and named reader: NOT-FOUND** (single-line "chorus observations and cohort references"; ships writer-only; no reader, no invented schema).
- **Topic 2/3 — Book-registration/instantiation ceremony with BMS: ABSENT / GAP-0010.**
