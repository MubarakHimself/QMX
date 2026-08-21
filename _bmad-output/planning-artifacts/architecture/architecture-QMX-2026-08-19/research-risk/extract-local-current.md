# QMX Risk Sitting — Local Corpus Extraction (Current Truth)

Scope note, read first: this corpus splits into two non-interchangeable layers.

- **Current ratified/provisional QMX corpus** — `docs/decisions/ADR-0008/9/10`, `docs/components/qmf-risk.md`, `docs/contracts/ct-22..25`, `docs/registry/variables.yaml`, `docs/glossary.md`, `docs/scenarios/SCN-0006`, `SCN-0010`, `tracker/trading-node-notes.md`. This is the authority. Its DEC ids run in the DEC-0039–DEC-0142 range in this reading.
- **Legacy GitBook capture, via `workroom/reference/05-trading-node-primer.md`** — an explicitly non-design "study primer" over an *old* GitBook baseline plus a flagged, non-authoritative `.recovery/` delta register. Its DEC ids (DEC-0002, DEC-0006, DEC-0008, DEC-0019…DEC-0055) and GAP ids (GAP-0001…GAP-0015) are a **separate, historical registry** — do not merge them with the current corpus's DEC/GAP numbering. Everything sourced from the primer below is marked **[legacy]**; content additionally marked **[later delta]** inside the primer is doubly non-authoritative (the primer's own author flags it as needing fresh ratification) and is reported here only where a future session would otherwise misread a term.

Per ADR-0010, the risk-vocabulary reset explicitly kills several legacy mechanisms (FORM-0006, DPR, PRS) and redefines R — so legacy math below is background only, never an executable answer.

---

## 1. Book schema

**Current corpus: not-found (explicitly gapped).** `CT-22` (Book and BMS charter contract) reserves the schema but assigns no fields:

```yaml
id: CT-22
name: Book and BMS charter contract
status: provisional
version: null
version_gap: GAP-0005
owner: COMP-QMF-RISK
consumers: []
active_consumers: []
intended_consumers: [COMP-QMF-REGISTRY]
wiring_status: reserved-unwired
layer_from: backend
layer_to: backend
decisions: [DEC-0039, DEC-0065, DEC-0066, DEC-0080, DEC-0095]
conflicts: [DEC-0067]
gaps: [GAP-0005, GAP-0018, GAP-0039, GAP-0040]
purpose: "Reserve an unwired Book and BMS charter placeholder pending the dedicated risk-boundary reconciliation."
invariants:
  - "Book and BMS express risk and money-management semantics, not trading-entry logic."
  - "The recovered Scalping Book is not a universal Book schema."
  - "No active Registry consumer or persistence handoff is assigned."
  - "The placeholder is not buildable until its caller, consumer, fields, and wiring are ratified."
  - "Bot cardinality, Book binding, BMS multiplicity, exit ownership, fields, mutability, inheritance, and signatures remain unresolved."
schema:
  type: null
  type_gap: GAP-0039
  fields: null
  fields_gap: GAP-0039
  enums: null
  enums_gap: GAP-0039
  units: null
  units_gap: GAP-0039
  nullability: null
  nullability_gap: GAP-0039
```
(`docs/contracts/ct-22-book-charter.yaml:1-33`)

`GAP(GAP-0039): Define Book and BMS fields, ownership, lifecycle, version compatibility, and BMS multiplicity; DEC-0095 remains open.` (`docs/components/qmf-risk.md:71`). Glossary: "Book fields, BMS cardinality, exit ownership, and account transitions remain `GAP(GAP-0039)`, `GAP(GAP-0040)`, and `GAP(GAP-0041)`." (`docs/glossary.md:54`).

**[legacy] found-with-citation, historical only.** Book def: *"A pod with charter, capital, roster, profile, rules, and journals. A book controls bots and never trades directly."* (`workroom/reference/05-trading-node-primer.md:41`, primer's DEC-0002). Six named slots — charter, capital, roster, profile, rules, journals (`primer:45-50`). Book template/instance split (ADR-0002 legacy): template is *"sealed Sections 0–5"* (grammar only); each instance (scalper) owns its own registry values; Section 6 is legacy `GAP-0001` (`primer:60-68`). Charter's four slots: *"game played, money shape, customer plus headline metric, and death condition"* (`primer:374`, legacy DEC-0027).

The seven doors, verbatim: *"The seven doors are footprint, viability veto, R_max, daily budget, breaker, exposure ledger, and kill switch."* (`primer:78`, legacy DEC-0035), with the ordering diagram `intent[CT-BOOK-01] --> footprint --> viability --> rmax --> budget --> breaker --> exposure --> ksa --> adapter` (`primer:82-94`). Door table (`primer:98-106`) quoted in full:

| # | Door | What it asks | Baseline backing |
| --- | --- | --- | --- |
| 1 | footprint | Inside the book's measured behaviour envelope; footprint measured in exam/live journals, not bot self-description; intent carries `footprint_version`. | `CT-BOOK-01` |
| 2 | viability veto | `FORM-0007`: `round_trip_cost_R / expected_edge_R <= v_cost`, `registry:viability_cost_fraction_max = 0.10`. | `capture/registry/formulas.md` |
| 3 | R_max | `FORM-0006`: `R_max_usd <= B * b * Lbar`; `Lbar` measured per bot at exam, never inherited. | `capture/registry/formulas.md` |
| 4 | daily budget | `FORM-0003`: `D = U / n`, re-derived at rollover, drains intraday. | DEC-0031 (legacy) |
| 5 | breaker | After `registry:scalper_breaker_threshold` consecutive stop-outs, benches to paper for the day, auto-resets next open. | DEC-0032 (legacy) |
| 6 | exposure ledger | BMS-desk measurement; cross-book cap authority = legacy `GAP-0008`, open. | `capture/components/book-management-system.md` |
| 7 | kill switch | KSA, above every book. | `capture/components/kill-switch-authority.md` |

`CT-BOOK-01` (trade intent envelope) fields named in the primer: `footprint_version`, `requested_r` (`primer:100,395`) — no full field list is quoted anywhere in the primer. `CT-BOOK-02` (Book Mode State) shares one enum `LIVE, PAPER, BENCHED, STOOD_DOWN` with `CT-BMS-02`; every record carries `reason` and `trigger_decision` matching `DEC-[0-9]{4}` (`primer:197`). **`CT-BOOK-03` is not found in the primer's baseline material at all** — it is named only inside the primer's own non-authoritative "later material" paragraph (dynamic SL/TP, CT-BOOK-03 attributes) and flagged **[later delta]**, itself excluded from this corpus (`primer:514`).

Versioned book-type schema: no version/compatibility rule is stated anywhere, legacy or current, beyond the template/instance split above.

---

## 2. BMS schema

**Current corpus: not-found (explicitly gapped).** No `CT-BMS-*` contract exists in `docs/contracts/`. Glossary: *"BMS: Versioned risk and money-management machinery owned within the Book domain. The documentation does not expand the initials because the authoritative sources do not fix an expansion. Schema, ownership, and multiplicity remain `GAP(GAP-0039)`."* (`docs/glossary.md:48-50`).

**[legacy] found-with-citation, historical only.** *"BMS accounts for and constrains books. It has Treasury, Exposure, Records, and Reporting desks, and it never trades, sizes, or reaches inside a book."* (`primer:227`, legacy DEC-0045). BMS diagram: `treasury -->|CT-BMS-01| records`, `exposure -->|CT-BMS-04| ksa`, `records --> reporting`, `records --> notify` (`primer:236-248`).

- `CT-BMS-01` (Treasury event): only `sweep`, `refund`, `re_seed` cross the book-to-treasury boundary (`primer:152`).
- `CT-BMS-02` (Mode Registry Read): *"the authoritative mode map"* — `LIVE, PAPER, BENCHED, STOOD_DOWN` (`primer:280,414`).
- `CT-BMS-03` (reconciliation): carries `virtual_equity`, `broker_equity`, `explained_delta`, `verdict` ∈ `reconciled | drift | unknown` (`primer:294,415`, `registry:reconciliation_epsilon = 0`, `operator_review: true`).
- `CT-BMS-04` (news block directive): Exposure desk → KSA (`primer:254`).
- `CT-BMS-05` (veto/refusal emission): *"Every refusal emits CT-BMS-05."* (`primer:110,456`).

BMS may/may-never (`primer:231-233`): *"May: own virtual ledger state, exposure measurement, mode registry, append-only journals, reporting metrics, KSA policy, and news block directives. May never: trade directly, mutate bot logic, overwrite journals in place, or bypass the veto ledger."*

Book-vs-BMS ownership table, quoted in full (`primer:272-284`):

| Question | Book | BMS |
| --- | --- | --- |
| May this trade happen? | Yes — the seven doors | No |
| How big is it? | Yes — offer/take per seat | No |
| Which bots are admitted? | Yes — roster, admission | No |
| Which global capabilities are on? | Yes — profile/dormant sockets | No |
| When is a bot leashed? | Yes — leash chain | No |
| What is the money actually worth? | No | Yes — Treasury virtual ledger |
| Authoritative mode of each book? | Emits `CT-BOOK-02` | Yes — `CT-BMS-02` |
| Permanent record? | No | Yes — Records |
| Exposed across books? | No | Yes — Exposure desk (v2 authority legacy `GAP-0008`) |
| Broker agreement? | No | Yes — reconciliation `CT-BMS-03` |
| KSA? | Obeys effects | Yes — owns policy |

---

## 3. Cardinalities

**Book ↔ BMS: not-found / explicitly open.** `qmf-risk.md` FM-8: *"One Book is assigned several BMS policies without a ratified multiplicity rule. The component must not select or merge them. `GAP(GAP-0039): Resolve DEC-0095.`"* (`docs/components/qmf-risk.md:112`). Same conflict flagged in `ct-22-book-charter.yaml:22` ("BMS multiplicity... remain unresolved") and `ADR-0008:35` ("Book/BMS schemas and BMS cardinality remain GAP-defined").

**Bot ↔ Book: found-with-citation, ratified.** *"Bot/confluence multiplicity is ratified... a Bot contains one-or-more confluences... Bot identity is its content. The Bot-Book-account binding is a separate dated binding record outside Bot identity: one Bot is bound to exactly one Book at any time, and re-binding (paper to live) never mints a new Bot, so paper and live performance stay comparable for alpha-decay sensing."* (`docs/components/qmf-risk.md:57-59`, DEC-0115). Confirmed in `SCN-0006:17,21` and glossary Bot entry (`docs/glossary.md:56-58`).

**Book ↔ account/venue: partially found, cardinality across venues not-found.** *"Books bind to accounts. An account carries a role (live, demo, paper-validation, paper-benched, or prop-firm), and Venue and Account are first-class nouns defined in `COMP-QMF-CORE` with their records owned by `COMP-QMF-REGISTRY`. The full Bot and Book schemas remain their own sittings."* (`docs/components/qmf-risk.md:61`, DEC-0107). Glossary Account entry: *"One Venue may hold many Accounts... Books bind to Accounts, not directly to Venues."* (`docs/glossary.md:22`). Neither source states whether one Book may bind accounts at several distinct venues simultaneously — not addressed either way.

---

## 4. Lifecycle states / modes

**Current corpus: fully gapped.** `CT-24` (Book mode and account-transition contract), verbatim:

```yaml
id: CT-24
name: Book mode and account-transition contract
status: provisional
version: null
version_gap: GAP-0005
owner: COMP-QMF-RISK
consumers: []
active_consumers: []
intended_consumers: [COMP-QMF-REGISTRY, COMP-QMF-DATA]
wiring_status: reserved-evidence-only
layer_from: backend
layer_to: backend
decisions: [DEC-0041, DEC-0070]
prohibitions: [DEC-0069]
gaps: [GAP-0005, GAP-0018, GAP-0019, GAP-0041]
purpose: "Reserve an unwired Book-mode evidence placeholder pending operator confirmation and GAP-0041."
authority_note: "A study-delivered recap records a Book-level, one-Bot-to-one-Book direction, but the direct operator wording is missing from the export; this is evidence only until operator confirmation."
invariants:
  - "Only a human may promote an artifact into the live zone."
  - "The recorded paper-mode recap is not an executable state or transition contract."
  - "CT-24 is evidence-only until the operator confirms the recap and GAP-0041 defines the full transition."
  - "No active Registry, Data, application, account, or execution consumer is wired."
  - "State values, transition triggers, account roles, rollback, duplicate prevention, continuity, and audit fields remain unresolved."
schema:
  type: null
  type_gap: GAP-0041
  fields: null
  fields_gap: GAP-0041
  enums: null
  enums_gap: GAP-0041
  units: null
  units_gap: GAP-0041
  nullability: null
  nullability_gap: GAP-0041
```
(`docs/contracts/ct-24-book-mode.yaml:1-34`)

Glossary explicitly flags the seat-state vs book-mode split as open: *"BENCHED: Do not assign BENCHED a canonical schema yet. The name is overloaded between Book mode and Bot seat state under `GAP(GAP-0045)`."* (`docs/glossary.md:518-520`).

**[legacy] found-with-citation, historical, and internally flagged as needing a split.** `CT-BOOK-02`/`CT-BMS-02` share **one enum**: `LIVE, PAPER, BENCHED, STOOD_DOWN`, each record carrying `reason` + `trigger_decision` (`primer:197`). Contract rules: *"Paper balances freeze at mode flip"*, *"Breaker bench-to-paper auto-resets at next open under DEC-0032"*, *"Other paper/live promotion, freeze, demotion, and return semantics remain GAP-0006"* (legacy) (`primer:197`). **[later delta]** K-26/C-02 already claim in the primer's own words that the four values *"mix two namespaces (Book mode vs roster-seat state) and must be split"* (`primer:199`) — i.e. the exact question the current corpus's GAP-0045 leaves open was already flagged, non-authoritatively, in the legacy delta register.

---

## 5. Book versioning + compatibility

**Not-found, current corpus.** Only a generic gap marker exists: *"...version compatibility..."* is listed among the unresolved items under `GAP-0039` (`docs/components/qmf-risk.md:71`; `docs/contracts/ct-22-book-charter.yaml:22`).

**Not-found, legacy corpus either.** No mention of a "scalping-book-v2" instance or a ledger-inheritance rule anywhere in `workroom/reference/05-trading-node-primer.md`. The template/instance split (§1 above) establishes that each instance owns its own registry values, but says nothing about version succession or ledger inheritance across versions of the same instance.

---

## 6. Exit ownership

**Current corpus: explicitly an open conflict, DEC-0067.** ADR-0008 consequences: *"Exit ownership remains the DEC-0067 conflict."* (`docs/decisions/ADR-0008-book-and-risk-boundary.md:35`). `qmf-risk.md` FM-2: *"A request depends on unresolved exit ownership... No exit policy may be inferred or routed. `GAP(GAP-0040): Resolve DEC-0067 before implementation.`"* (`docs/components/qmf-risk.md:106`). `GAP(GAP-0040): Resolve whether Book owns every exit policy or mediates ordinary Bot exits; DEC-0067 remains a conflict.` (`docs/components/qmf-risk.md:73`). `CT-22` and `CT-23` both list `conflicts: [DEC-0067]` (`docs/contracts/ct-22-book-charter.yaml:14`, `docs/contracts/ct-23-risk-evaluation.yaml:15`). Glossary Exit entry: *"Whether ordinary exits are Bot organs or all exit policy belongs to the Book remains `GAP(GAP-0040)`."* (`docs/glossary.md:150`). Repeated as open in `SCN-0006:17,25` and `SCN-0010:17,25,29,37`.

**[legacy] found-with-citation — but this legacy answer is NOT treated as ratified by the current corpus (see Contradictions).** *"The bot owns market-facing entry and exit organs. The book owns admission, sizing, doors, leash, and profile selection."* (`primer:162`, legacy `capture/system-constitution.md`, Authority Hierarchy). Glossary(legacy) Bot: *"A bot owns entry logic and exit organs while book infrastructure owns admission and sizing."* (`primer:163,368`). Named forced-exit powers, all Book/leash-side (`primer:167-174`): **hold-time force-flat** (leash rung 7, "named once and never defined"); **kill-line stand-down** (equity crosses K, book flips to paper, semantics = legacy `GAP-0006`); **classed kill switch** (KSA effect at the Adapter, never bot-readable advice); **day closure** (leash rung, "named once, never defined"). **[later delta]** dynamic SL/TP framing (*"belongs to Book money-rule grammar, with BMS configuration authority and Adapter enforcement... globally uniform stop service is rejected"*) and open position-fate-at-boundary questions are explicitly flagged non-baseline (`primer:174`).

Position-safety / SL-TP authority beyond the above: no source, legacy or current, states who moves stops dynamically as a ratified rule — the only concrete legacy statement is itself flagged **[later delta]**.

---

## 7. Paper mode

**Current corpus: provisional/evidence-only.** ADR-0009 (status: provisional, requires operator confirmation): *"Paper operation is a Book-level state: a Book that cannot trade live directs its attached Bot activity to the Book's paper account so evidence continues."* (`docs/decisions/ADR-0009-book-level-paper-mode.md:31`, DEC-0070). Consequence: *"The direct operator wording is absent from the SRC-01-C0022 transcript export; DEC-0070 survives through the immediate SRC-01-C0023 recap. Account mapping, transitions, and duplicate prevention remain GAP-defined until the operator confirms the recap."* (`ADR-0009:35`). Option 1 (parallel Bot paper twins) is dead: *"dead because it duplicates Bot identity and Book attachment (DEC-0069)."* (`ADR-0009:25`). `CT-24` (§4 above) is `wiring_status: reserved-evidence-only`.

Ratified pieces that de-risk future paper-mode design: account role (not world) carries money-reality — *"a paper or demo account is `world = live` and stays comparable to live for alpha-decay sensing"* (`SCN-0006:17,21`, DEC-0110, DEC-0107); Bot-Book-account rebind never mints a new Bot (`qmf-risk.md:59`, DEC-0115); glossary World entry: *"a non-live world may never write into the live evidence namespace... storage separation... delivers world separation"* (`docs/glossary.md:506`).

Not ratified: transition triggers, duplicate-order prevention mechanism, live↔paper state machine, rollback, audit — all under `GAP-0041` (`docs/components/qmf-risk.md:75`).

Paired demo (adjacent, venue-sitting territory but inherited): glossary *"Paired demo: A demo binding run simultaneously alongside a live binding under the venue's declared session topology (two connections where demo and live are separate hosts). Paired-demo bindings are secret-reference-only records... a shared-account order-lifecycle merge uses only the caller's sequencer evidence, never a venue-side id."* (`docs/glossary.md:268-270`, DEC-0138). `tracker/trading-node-notes.md:8`: *"Demo and live are separate cTrader hosts; serving both simultaneously REQUIRES two connections... This is the mechanism for the corpus's paired-demo fail-safe rule (K-27)."* (K-27 is a venue-sitting id, not defined further within this corpus.)

**Open contradiction on record**, not resolved by any source read: `tracker/trading-node-notes.md:25`: *"Paper-mode scope: fail-mechanism-only (K-25 delta) vs standing-state feeding alpha-decay (tracker/map.md, ticket 002). Risk-sitting item (GAP-0041)."*

**[legacy]** *"Paper mode is diagnostic. It freezes the counterfactual balance at flip and preserves evidence after a breaker, kill-line stand-down, or demotion."* (`primer:315`, legacy L13/DEC-0014). *"The only ratified transition is the breaker path: after `registry:scalper_breaker_threshold` consecutive stop-outs, bench to paper for the rest of the day and auto-reset at next open (DEC-0032)."* Everything else — kill-line stand-down, discretionary promotion, freeze, demotion, non-breaker return-to-live — is legacy `GAP-0006` (`primer:315`).

---

## 8. News protection

**Current corpus: windows unratified, pair-scoping ratified.** ADR-0010: *"News controls remain pair-scoped..."* (`docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:31`). `qmf-risk.md`: *"News control is pair-scoped and separate from SQS. SQS means Spread Quality Sensor. Exact windows and the SQS formula remain unresolved at `registry:news_blackout_before`, `registry:news_blackout_after`, and `registry:spread_quality_sensor_formula`."* (`docs/components/qmf-risk.md:51`). Registry entries, verbatim:

```yaml
- name: news_blackout_before
  symbol: null
  value: null
  formula: null
  units: minutes
  type: duration
  component: COMP-QMF-RISK
  decision: DEC-0072
  configurable: true
  gap: GAP-0042
  notes: "Fifteen minutes was tentative and is not a live value."

- name: news_blackout_after
  symbol: null
  value: null
  formula: null
  units: minutes
  type: duration
  component: COMP-QMF-RISK
  decision: DEC-0072
  configurable: true
  gap: GAP-0042
  notes: "Fifteen minutes was tentative and is not a live value."
```
(`docs/registry/variables.yaml:438-460`)

`GAP(GAP-0042): Define pair-scoped news windows, severities, mappings, open-position behavior, and overrides.` (`docs/components/qmf-risk.md:77`). `CT-25` invariant: *"News blocking is pair-scoped and distinct from SQS."* (`docs/contracts/ct-25-risk-journal.yaml:17`).

Severity tiers, currency→instrument mapping, open-position behavior, overrides: **not found anywhere in current corpus**, only named as unresolved via GAP-0042.

**[legacy]** `CT-BMS-04` news block directive: refuses entries *"for live and paper alike"*; refusal signs the veto ledger; *"no paper data is collected under a known invalid news window"* (legacy L9/DEC-0010) (`primer:254`). No minutes, severity tiers, or currency-mapping formula appear even in the legacy source — the primer states only that a directive exists and its refusal scope, nothing more.

---

## 9. SQS / spread-quality sensing

**Current corpus: name ratified, formula/inputs/thresholds/cadence unratified.** ADR-0010: *"SQS means Spread Quality Sensor"* (`docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:31`, DEC-0074). Registry entry, verbatim:

```yaml
- name: spread_quality_sensor_formula
  symbol: SQS
  value: null
  formula: null
  units: null
  type: formula
  component: COMP-QMF-RISK
  decision: DEC-0075
  configurable: false
  gap: GAP-0043
  notes: "SQS means Spread Quality Sensor; its formula is explicitly unratified."
```
(`docs/registry/variables.yaml:462-472`)

Glossary: *"SQS: Spread Quality Sensor. SQS is distinct from news control. Formula, inputs, thresholds, cadence, and stale-data behavior remain `GAP(GAP-0043)`."* (`docs/glossary.md:408-410`). Retired-names section: *"Snapshot Quality Sensor: Incorrect expansion of SQS. Use SQS."* (`docs/glossary.md:550-552`) — this is the current corpus explicitly rejecting "Snapshot" as an expansion. `GAP(GAP-0043): Define SQS inputs, units, formula, thresholds, cadence, hysteresis, and stale-data behavior.` (`docs/components/qmf-risk.md:79`).

**WHY it existed — not clearly answered in any source.** No corpus text states SQS's purpose beyond gating; the closest is the legacy door-blocking mechanic below.

**[legacy]** The GitBook capture never expands the acronym at all; it appears only as `CT-MIS-01` fields `sqs_score` and `sqs_hard_block`, with the rule *"SQS unreachable → Door performs hard block."* (`primer:305-306,421`). **[later delta]** K-38/D-09 define it, non-authoritatively, as *"snapshot quality score, never a queue"* — this directly contradicts the current ratified "Spread" expansion (see Contradictions).

---

## 10. Kill switch / KSA

**Current corpus (docs/): no KSA contract or definition of any kind exists.** Searched `qmf-risk.md`, all four CT files, and `docs/glossary.md`: none contain the string "KSA" or "kill switch" as a defined term. This risk-module component text is silent on kill-switch authority entirely.

**Venue-sitting inheritance (tracker/trading-node-notes.md — ratified upstream, explicitly handed to the risk/node sittings):**
- *"Protection funnel: MIS senses → KSA decides (escalate-only; human A1 de-escalates) → Adapter enforces as an effect. Flatten authority was explicitly unassigned — the venue sitting's GAP-0036 ruling reserves it as a human-authorized path, never assumed, never automatic (policy assignment lands in the risk/node sittings)."* (`tracker/trading-node-notes.md:42`) — GAP-0036 here is a venue-sitting gap id, distinct from the risk module's GAP-0039..0046.
- *"Protection commands (cancel/close/close_all) dispatch ahead of place_order on shared throttles; suspend-new takes local effect instantly. close_position/close_all carry a required typed scope (account \| account-binding \| instrument-within-binding) — the node's kill path must state its scope."* (`tracker/trading-node-notes.md:48`)

**[legacy] found-with-citation, historical only.** *"KSA is the global protection state machine. BMS owns policy, the trading node enforces effects through the adapter, and bots never see KSA directly."* (`primer:308-309`, legacy DEC-0008). Five levels: **GREEN, YELLOW, ORANGE, RED, BLACK** (legacy DEC-0043). Four trigger classes: **`scheduled_news`, `black_swan`, `connectivity`, `unknown_state`** (legacy DEC-0044). Law L8: automatic transitions **escalate only**; de-escalation requires A1 human authority. Dead idea: **TIGHTEN half-size** (legacy DEC-0019) — *"trading half-size through bad conditions still pays to lose."* *"The full trigger-to-level target matrix is `GAP-0015` [legacy], open — the page says outright 'do not invent target state here.'"* (`primer:309`)

Effect-vocabulary note: the current corpus's own word **suspend-new** appears (`tracker/trading-node-notes.md:48`); **drain** as an effect word does **not appear anywhere in this corpus**, legacy or current — not-found. The legacy Adapter's four-command vocabulary is `place_order, cancel_order, close_position, close_all` (`primer:165,312,430`).

---

## 11. Correlation ledger / correlation rules

**Current corpus: minimal.** ADR-0008 decision line: *"COMP-QMF-RISK owns versioned Book and BMS semantics, money and position-sizing policy, surgical risk controls, and correlation evidence."* (`docs/decisions/ADR-0008-book-and-risk-boundary.md:31`, part of the DEC-0065/0066/0068/0080 decision). No further computation-vs-enforcement definition appears anywhere in `qmf-risk.md`, the CT files, glossary, or the SCNs — "correlation" does not otherwise appear as a defined term in the current corpus's risk-domain text.

**Confirmed as a live (not dead) concept, venue-sitting audit:** *"Vocabulary the operator half-remembered — AUDITED, definitive (order-path study, 2026-08-20): correlation ledger LIVE (one of the five Records streams); DPR + PRS DEAD by operator ruling DEC-0093 ('legacy-only; must not return as risk controls')..."* (`tracker/trading-node-notes.md:31`).

**[legacy]** Correlation ledger, one of five journals: *"Chorus observations and cohort references"*, owner COMP-BMS (`primer:264,413`). Chorus flag: *"Automatic listener for abnormal loss shape. The chorus owns rate and clustering shape, not amount lost."* (`primer:387`, legacy DEC-0048 [note: this is the **legacy** DEC-0048, a different decision from the current corpus's DEC-0048 governing the seven journal event types — same number, two registries, see Contradictions]). Its frequency rule `registry:chorus_expected_frequency_rule` is legacy-`null`/`GAP-0012`; thresholds come from cohort exam observations `CT-EXAM-02` (`primer:188`).

What is computed vs enforced: the legacy source states only that chorus/correlation is *sensed* (an "automatic listener") and its output feeds the leash chain as one rung ("chorus flag", `primer:383,386`) — enforcement mechanics beyond that are not specified even in the legacy material.

---

## 12. Money ladder + R

**R — current corpus, ratified.** Registry entry, verbatim:

```yaml
- name: original_risk_unit
  symbol: R
  value: 1
  formula: null
  units: pre-trade-risk-unit
  type: ratio
  component: COMP-QMF-RISK
  decision: DEC-0076
  configurable: false
  notes: "R is exactly one unit of original pre-trade risk; it is not profit, equity, or post-trade return."
```
(`docs/registry/variables.yaml:427-436`)

ADR-0010: *"R uses `registry:original_risk_unit`"* (`docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:31`). `qmf-risk.md`: *"The meaning of R is defined only by `registry:original_risk_unit`; this spec does not restate that non-null registry value or substitute realized-profit, equity, or post-trade-return semantics for it."* (`docs/components/qmf-risk.md:49`, DEC-0076). Glossary: *"R: The canonical original pre-trade risk unit referenced by `registry:original_risk_unit`. R does not mean realized profit, account equity, or post-trade return."* (`docs/glossary.md:344-346`).

**FORM-0006 — current corpus, explicitly dead.** ADR-0010 rejected options: *"Implement recovered FORM-0006 — dead because it is dimensionally invalid under the corrected meaning of R (DEC-0077)."* (`docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:25`). `qmf-risk.md` never-list: *"...or revive the dead FORM-0006, DPR, PRS, auctions, or legacy slot machinery."* (`docs/components/qmf-risk.md:23-24`, DEC-0077/0079/0093). Glossary retired-names: *"FORM-0006: Dead legacy formula. FORM-0006 is dimensionally broken and must not be implemented."* (`docs/glossary.md:530-532`). `GAP(GAP-0044): Replace dead FORM-0006 with dimensionally valid formulas and distinct capital concepts.` (`docs/components/qmf-risk.md:81`). FM-3: any payload using dead FORM-0006/DPR/PRS/auctions/legacy slots *"is inadmissible and cannot enter CT-23; it returns a `policy rejection` refusal..."* (`docs/components/qmf-risk.md:107`).

**FORM-0004, D/B/b/Lbar, treasury seed-to-cap/sweep, offer/take mechanics: not-found anywhere in the current corpus** (not in ADRs, `qmf-risk.md`, any CT, glossary, variables.yaml, or the two SCNs). ADR-0010 states only that *"roster state, risk allocation, and any surviving legacy capital concept remain distinct"* (`docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:31`) without naming or defining them.

**[legacy] found-with-citation, historical only — all of the below is superseded/uncertain given DEC-0077's dead-FORM-0006 ruling above, and is presented for background, not as an answer:**

| Rung | Formula | Meaning | Scalper-instance values |
| --- | --- | --- | --- |
| Cap | `FORM-0001` `C = cap_multiple * S` | Cycle finish line, checked at rollover only | `scalper_seed_capital` S = 500 USD, `scalper_cap_multiplier` 2.5 |
| Runway | `FORM-0002` `U = E - K` | Money above the kill line | `scalper_kill_line` K = 200 USD |
| Daily budget | `FORM-0003` `D = U / n` | Runway burn allowed today | `scalper_runway_divisor` n = 5 |
| Offer per seat | `FORM-0004` `offer_R_usd = D / (B * b * Lbar)` | What the book offers a seat | `scalper_breaker_threshold` B = 2, `scalper_budget_shaping_factor` b = 2, `scalper_mean_loss_r` Lbar = measured per bot at exam |
| Take per seat | `FORM-0005` `take_R_usd = min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)` | Bot takes the smaller of offer and its own Kelly sizing | — |

(`primer:117-129`, `capture/registry/variables.md`, `capture/registry/formulas.md`)

`Lbar` warning: *"Measured per bot at exam; 0.35R is a reference expectation only and never an inherited bot default."* Kelly half deliberately unfinished: *"Formula is ratified; the trust-bounded cost-aware Kelly implementation remains a bot/book validation responsibility."* (`primer:127-128`). Constitutional rule: legacy Law L4/DEC-0021 — *"Unclaimed or freed budget is never redistributed in-cycle."* (`primer:131`).

Treasury seed-to-cap + sweep (`primer:133-156`, legacy): *"The cycle is seed to cap. The book compounds within a cycle and ratchets between cycles."* (DEC-0006 legacy). *"Sweep is checked at rollover only. If cap is hit intraday, the book completes the day and sweep uses rollover equity."* (DEC-0038 legacy). Only `sweep`, `refund`, `re_seed` cross the book-to-treasury boundary (`CT-BMS-01`). Refund reserve `FORM-0008`: `reserve_usd ~= rho * N_cycles_month * S`, with `rho` and `N_cycles_month` both legacy-`null`/`GAP-0007` (`primer:252`). Dead paths: mid-cycle top-up (legacy DEC-0020) and live restart from kill-line remnant (legacy DEC-0023).

Distinct capital concepts: current corpus states the requirement (ADR-0010:31 above) but does not enumerate them; legacy has seed/kill-line/cap/runway/daily-budget/offer/take (money ladder) plus Treasury's separate virtual ledger — none of these are declared "the" ratified distinct-capital-concepts set by the current corpus.

---

## 13. Stop-out

**Current corpus: explicitly unresolved, including the breakeven ambiguity and the B=2 counter.** Registry entry, verbatim:

```yaml
- name: bench_stopout_threshold
  symbol: null
  value: null
  formula: null
  units: consecutive-stop-outs
  type: count
  component: COMP-QMF-RISK
  decision: DEC-0094
  configurable: true
  gap: GAP-0045
  notes: "A reported value of two is unusable until stop-out and BENCHED semantics are reconciled."
```
(`docs/registry/variables.yaml:474-484`)

```yaml
- name: bench_reset_boundary
  symbol: null
  value: null
  formula: null
  units: null
  type: enum
  component: COMP-QMF-RISK
  decision: DEC-0094
  configurable: true
  gap: GAP-0045
```
(`docs/registry/variables.yaml:486-495`)

Glossary: *"Stop-out: An unresolved risk event term. Whether breakeven or other closes count and how stop-out drives BENCHED state remain `GAP(GAP-0045)`."* (`docs/glossary.md:432-434`) — this directly and explicitly leaves the breakeven-exit ambiguity open. `GAP(GAP-0045): Define stop-out, benchmark/roster terminology, bench behavior, and fresh alpha-decay evidence.` (`docs/components/qmf-risk.md:83`).

**[legacy]** The B=2 number the current corpus calls "unusable" traces to: *"After `registry:scalper_breaker_threshold` consecutive stop-outs the bot benches to paper for the rest of the day and auto-resets at next open."* (`primer:104`, legacy DEC-0032), with the scalper-instance value `scalper_breaker_threshold` **B = 2** (`primer:122`). No legacy source defines whether a breakeven close counts as a stop-out either — the primer's own vocabulary table lists "Breaker" only as the counter mechanic, not the definition of what counts as a loss.

---

## 14. Alpha-decay evidence classes

**Current corpus: named as a future requirement, not defined.** `GAP(GAP-0045): Define stop-out, benchmark/roster terminology, bench behavior, and fresh alpha-decay evidence.` (`docs/components/qmf-risk.md:83`). The only substantive current-corpus fact is the *reason* alpha-decay sensing must stay possible: Bot-Book rebind never mints a new Bot, "so paper and live performance stay comparable for alpha-decay sensing" (`docs/components/qmf-risk.md:59`, DEC-0115; `SCN-0006:17,21`, DEC-0110/0107).

**"The Book sets the bar" / qualification metrics / exam certificates / certified footprint: not found verbatim anywhere, current or legacy.** The closest legacy concept is the Examination engine: *"certifies whether a bot can join a specific book... gates on exactly two things: the edge is real after costs, and the candidate is not fiction (DEC-0036 [legacy]). Everything else becomes measured input for the book wallet, leash, and chorus."* (`primer:320-321`). Exam certificate `CT-EXAM-01` pins *"labeler versions, EV by regime, mean loss, fire-rate band, breaker expectation, cost ratio"* (`primer:432`). "Footprint" is the closest thing to "certified footprint": *"measured in exam and live journals, not accepted from bot self-description"* (`primer:100,375`, legacy DEC-0035). None of this is present in the current ratified corpus at all.

---

## 15. Book/BMS validation leads

**Not-found, current corpus and legacy corpus alike.** No text in `docs/` describes how a *Book* or *BMS* itself proves itself before carrying money. The legacy Examination engine (§14 above) certifies a **bot** against a specific book — *"A bot is not validated in the abstract; it is validated against the book contract it applies to join"* (`primer:320-321`) — but nothing, in either corpus layer, addresses the Book or BMS's own qualification process. This is a genuine gap in both layers, not just the current one.

---

## 16. Same-tick priority / no-overnight / dead-zone

**Current corpus: priority explicitly unresolved.** `GAP(GAP-0046): Define deterministic same-tick priority and Book-specific overnight behavior.` (`docs/components/qmf-risk.md:85`). Repeated in `SCN-0010:17,29,37,41` ("Bot multiplicity is ratified as one-or-more at every layer (DEC-0115), but that is a cardinality rule, not a risk arithmetic.").

**Dead-zone — found-with-citation, ratified as policy direction, matches the checklist's ~45min figure.** *"Dead zone: ~45-minute relax around session handover (analysis-before-execution; from the first QMX version, operator-solved ~Dec 2025). Operator clarification 2026-08-20: the dead zone pauses TRADING ONLY — data streaming continues throughout; it is NOT kill-switch logic. Related note: real session activity starts later than nominal opens... session-open cross-referencing is a node-era refinement. Risk-sitting policy."* (`tracker/trading-node-notes.md:18`).

No-overnight policy / hold limits: not found in any file read — no source states a hold-time limit or an overnight-flat rule as ratified. The only adjacent legacy item is "hold-time force-flat" (leash rung 7), which the primer itself says is *"named once and never defined anywhere in the capture"* (`primer:169,390`).

Priority among protective stops / Book force-flat / kill switch / fast invalidation / discretionary exits: not resolved anywhere. **[legacy]** only an escalation *order* for the leash chain exists — *"ambient governor, day closure, bench-to-paper, chorus flag, kill-line stand-down, classed kill switch, and hold-time force-flat"* (`primer:178`, legacy DEC-0037) — and most of those rungs are themselves undefined (`primer:191`: *"ambient governor, day closure, classed kill switch target levels, and hold-time force-flat are named but never defined in the capture"*). This is a leash-escalation order, not a same-tick simultaneous-action priority rule, so it does not answer GAP-0046 even as background.

---

## 17. Multi-currency

**Not-found, substantively.** No file in this corpus addresses account numeraire, cross-account aggregation, or FX conversion for risk math. The single tangential fact, from venue-sitting inheritance: *"No direct equity field — equity must be derived (balance + quote-currency unrealized PnL) (K-54, corpus)."* (`tracker/trading-node-notes.md:15`) — this is an adapter/equity-derivation fact (quote-currency PnL), not a risk-domain numeraire or cross-account FX policy, and it is not further developed anywhere.

---

## DEC id status (current corpus registry, DEC-0039–DEC-0142 range)

Status is as characterized by the corpus text itself — this is not a decision ledger and I hold no access to one; where no explicit qualifier exists, the DEC is reported as "cited, not flagged open/dead" rather than declared ratified.

| DEC | Status as evidenced | Citation |
| --- | --- | --- |
| DEC-0039 | Cited as settled/ratified background (reserved-contract posture, Bot-Book-account binding); not flagged open, dead, or conflicting anywhere read. | `qmf-risk.md:21`, `SCN-0006:21` |
| DEC-0040 | **Superseded** by DEC-0115 (Bot-to-confluence cardinality). | `qmf-risk.md:116` |
| DEC-0041 | Ratified — human-only promotion occurrence card. | `qmf-risk.md:109`, `SCN-0006:35` |
| DEC-0048 | Ratified — journal's seven event types incl. risk transition. | `qmf-risk.md:111` |
| DEC-0065 | Provisional/accepted-directionally — COMP-QMF-RISK owns versioned Book/BMS semantics. | `ADR-0008:31` |
| DEC-0066 | Provisional/accepted-directionally — same decision as DEC-0065. | `ADR-0008:31` |
| DEC-0067 | **Open conflict** — exit ownership. | `ADR-0008:35`, `ct-22:14`, `ct-23:15` |
| DEC-0068 | Provisional/accepted-directionally, part of the ADR-0008 decision. | `ADR-0008:31` |
| DEC-0069 | **Dead** — parallel Bot paper-twin design. | `ADR-0009:25`, `ct-24:14` |
| DEC-0070 | Recorded but **evidence-only pending operator confirmation** — Book-level paper mode. | `ADR-0009:31,35` |
| DEC-0071 | **Dead** — special blackout simulator. | `ADR-0009:26` |
| DEC-0072 | Provisional — pair-scoped news, part of ADR-0010 decision. | `ADR-0010:31` |
| DEC-0074 | Provisional — SQS = Spread Quality Sensor. | `ADR-0010:31` |
| DEC-0075 | Cited — SQS formula explicitly unratified. | `variables.yaml:469` |
| DEC-0076 | Ratified — R = `registry:original_risk_unit`. | `ADR-0010:31`, `variables.yaml:434` |
| DEC-0077 | **Dead-making** — FORM-0006 ruled dimensionally invalid under corrected R. | `ADR-0010:25` |
| DEC-0078 | Provisional, part of ADR-0010 decision (roster/allocation/capital distinctness). | `ADR-0010:31` |
| DEC-0079 | **Dead** — DPR/PRS donor-only material. | `ADR-0010:26` |
| DEC-0080 | Provisional/accepted — recovered Scalping Book is one pattern, not universal. | `ADR-0008:31`, `qmf-risk.md:47` |
| DEC-0092 | Provisional, part of ADR-0010 decision. | `ADR-0010:31` |
| DEC-0093 | **Dead** — DPR/PRS "legacy-only; must not return as risk controls" (operator ruling). | `ADR-0010:26`, `trading-node-notes.md:31` |
| DEC-0094 | Cited — governs bench_stopout_threshold / bench_reset_boundary, both unresolved (GAP-0045). | `variables.yaml:481,493` |
| DEC-0095 | **Open** — BMS multiplicity/cardinality. | `qmf-risk.md:71,112` |
| DEC-0101 | Ratified — tier-1 ruff/pyright/pytest governance. | `qmf-risk.md:67` |
| DEC-0105 | Ratified — money path scaled-integer, float ban. | `qmf-risk.md:65` |
| DEC-0107 | Ratified — Account/Venue as core nouns; Books bind to Accounts. | `qmf-risk.md:61`, `SCN-0006:17,21` |
| DEC-0109 | Ratified — seven-category typed refusal taxonomy. | `qmf-risk.md:107` |
| DEC-0110 | Ratified — account role (not world label) carries money-reality. | `SCN-0006:17,21` |
| DEC-0111 | Ratified — benchmark harness requirement. | `qmf-risk.md:67` |
| DEC-0112 | Ratified — typed refusal, correlation_id, health(). | `qmf-risk.md:67` |
| DEC-0113 | Ratified — QMF values immutable, no threads/background work. | `qmf-risk.md:65` |
| DEC-0115 | **Ratified** — Bot contains one-or-more confluences; one Bot bound to exactly one Book; rebind never mints new Bot. | `qmf-risk.md:57-59`, `SCN-0006:17`, `SCN-0010:17` |
| DEC-0116 | Ratified — human-signed promotion occurrence, plain-words summary is identity field. | `qmf-risk.md:109`, `SCN-0006:35` |
| DEC-0119 | Ratified — journal gapless per-writer sequences, seven event types. | `qmf-risk.md:111` |
| DEC-0120 | Ratified — default-deny package dependency; risk-owns-nothing-else. | `qmf-risk.md:69` |

**Legacy GitBook DEC ids** (DEC-0002, DEC-0003, DEC-0004, DEC-0006, DEC-0008, DEC-0010, DEC-0011, DEC-0012, DEC-0014, DEC-0017, DEC-0019 through DEC-0048, DEC-0055) are a **separate, non-authoritative historical registry**, cited only inside `workroom/reference/05-trading-node-primer.md`. None of them carry current-corpus ratification status; several govern mechanisms the current corpus has since killed (DEC-0077/0079/0093 above) or left as unresolved conflicts (DEC-0067) rather than adopting the legacy answer.

---

## Contradictions

1. **SQS expansion.** Current ratified corpus: *"SQS means Spread Quality Sensor"* (ADR-0010, DEC-0074/0075) — `docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:31`, `docs/registry/variables.yaml:472`, and the glossary explicitly retires "Snapshot Quality Sensor" as an *incorrect* expansion (`docs/glossary.md:550-552`). Legacy GitBook baseline never expands the acronym at all (`workroom/reference/05-trading-node-primer.md:306,421`); a non-authoritative **[later delta]** inside that same primer (K-38/D-09) claims the opposite expansion — *"snapshot quality score, never a queue"* (`primer:306,421`). The current corpus's own retired-name entry directly contradicts that delta's claim.

2. **Exit ownership.** Legacy baseline states a flat rule: *"The bot owns market-facing entry and exit organs. The book owns admission, sizing, doors, leash, and profile selection."* (`primer:162-165`). The current ratified corpus does **not** adopt this as settled — it treats the identical question as an unresolved conflict, DEC-0067, requiring the risk sitting to rule (`docs/decisions/ADR-0008-book-and-risk-boundary.md:35`; `docs/components/qmf-risk.md:73,106`; `docs/contracts/ct-22-book-charter.yaml:14`; `docs/contracts/ct-23-risk-evaluation.yaml:15`).

3. **R's mathematical role.** Legacy FORM-0004/FORM-0006 (`primer:102,122,393-395`) use R as a formula output scaled by measured `Lbar`, breaker count `B`, and shaping factor `b` (`R_max_usd <= B * b * Lbar`). The current corpus explicitly kills FORM-0006 as *"dimensionally invalid under the corrected meaning of R"* (DEC-0077) (`docs/decisions/ADR-0010-risk-vocabulary-clean-start.md:25`) while ratifying R as a fixed unit, `value: 1`, `type: ratio` (`docs/registry/variables.yaml:427-436`) — the legacy math and the current ratified unit are stated to be dimensionally incompatible.

4. **Bench/BENCHED namespace.** Legacy baseline uses a single shared enum `LIVE, PAPER, BENCHED, STOOD_DOWN` across both `CT-BOOK-02` (Book mode) and `CT-BMS-02` (mode registry) (`primer:197,414`). The current corpus's glossary explicitly refuses to treat this as settled: *"The name is overloaded between Book mode and Bot seat state under `GAP(GAP-0045)`."* (`docs/glossary.md:518-520`). A non-authoritative legacy delta (K-26/C-02, itself inside the primer) had already flagged the same split need (`primer:199`) — so all three layers agree a split is needed, but none ratifies what the split looks like.

5. **bench_stopout_threshold B=2.** The legacy scalper-instance value `scalper_breaker_threshold = 2` (`primer:122`) is the exact number the current ratified registry entry calls out and rejects as usable: *"A reported value of two is unusable until stop-out and BENCHED semantics are reconciled."* (`docs/registry/variables.yaml:484`).

6. **DEC-0048 numbering collision.** The current corpus's DEC-0048 governs the journal's seven event types (`docs/components/qmf-risk.md:111`). The legacy corpus's DEC-0048 (a different, historical registry) governs the chorus-flag definition (`workroom/reference/05-trading-node-primer.md:387`). Same number, two unrelated rulings in two non-interchangeable registries — a citation-hygiene hazard for any future session that pastes a bare "DEC-0048" without stating which registry it means.

7. **GAP numbering namespaces.** Three distinct GAP registries are visible in this corpus: (a) the current risk module's own `GAP-0039`–`GAP-0046` (`docs/components/qmf-risk.md:71-85`); (b) other current-corpus gaps cited inline in the CT files — `GAP-0005, GAP-0007, GAP-0011, GAP-0016, GAP-0017, GAP-0018, GAP-0019, GAP-0025` (e.g. `docs/contracts/ct-22-book-charter.yaml:5,15`, `ct-25-risk-journal.yaml:14,23,27,29`) — whose definitions are not in this corpus; and (c) the legacy GitBook's own `GAP-0001`–`GAP-0015` (`primer:486-507`). Numbers overlap across (a)/(b) vs (c) (e.g. legacy GAP-0005 = "Broker/cTrader feasibility," `primer:493`, vs current corpus's own GAP-0005 appearing only as a bare `version_gap`/`gaps` reference with no definition in this corpus). Do not merge these without confirming which registry a bare "GAP-000N" belongs to.

---

## Not-found list

Topics with no direct evidence for the actual question asked, in either corpus layer (a bare GAP marker restating "this is undefined" does not count as evidence of content, and is reported inline above where it exists):

- **Topic 5 — Book versioning + compatibility.** No source states a version-succession or ledger-inheritance rule (e.g. "scalping-book-v2 = new Book, never inherits v1 ledger") anywhere, current or legacy.
- **Topic 15 — Book/BMS validation leads.** No source, current or legacy, describes how a *Book* or *BMS* itself proves itself before carrying money. (The legacy Examination engine certifies a *bot* against a book, which is a different question.)
- **Topic 17 — Multi-currency risk math.** No source addresses account numeraire, cross-account aggregation, or FX conversion for risk math; the only adjacent fact is an equity-derivation note (`tracker/trading-node-notes.md:15`) unrelated to risk-domain FX policy.
