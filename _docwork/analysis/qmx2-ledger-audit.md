# QMX2-side Stage 3 ledger audit

**Purpose:** acceptance checklist for `_docwork/ledger.yaml` and `_docwork/gaps.yaml`, using the later QMX2 source only (`EXT-0001`–`EXT-0271`) and the cross-source reconciliation. This file does not ratify studies or edit either artifact.

## Audit rules that must govern the merge

1. **Chronology beats polish.** Direct operator corrections outrank assistant research, map/spec edits, and older decisions. The tracker/map was explicitly described as unverified; examples must not harden into requirements. Research is never auto-adopted. [EXT-0007, EXT-0035, EXT-0040, EXT-0041]
2. **Preserve evidence class.** `accepted`, `direction agreed`, `recorded ruling with direct words unavailable`, `study delivered/pending ratification`, `own session`, and `agentic era` are not interchangeable.
3. **Preserve reversals.** Earlier designs need `superseded`/`dead` entries with reasons, not silent deletion. The most dangerous zombies are the kernel, universal card, Program/Campaign, bundled Broker Exam, agent page, bot paper twin, `qmf-mis`, and “minimal core.”
4. **Do not launder studies into rulings.** The registry three-discipline model, six-layer data blueprint, exact storage stack, and answer-key catalog were explicitly delivered as studies rather than adopted designs. [EXT-0193–EXT-0203]
5. **Collapsed-source caveat:** part of the operator’s long answer in `SRC-01-C0022` is absent from the export. Several later rulings survive only through the assistant’s immediate recap in C0023. They may enter the ledger, but their rationale/status must say `recorded operator ruling; direct wording unavailable`, not pretend a direct quote exists. [EXT-0213–EXT-0216]

## Must-have final live decisions

### Foundation and authority

| Ledger must say | Evidence |
|---|---|
| QMF is an open toolbox used to build applications, not the QMX application or trading-node runtime. | EXT-0013, EXT-0108 |
| QMF remains interoperable with normal Python and external methods/libraries; uniformity comes from shared contracts and order, not walls. | EXT-0025–EXT-0030, EXT-0045, EXT-0109 |
| The framework foundation stays asset/venue/strategy neutral so equities and crypto extend it rather than rebuild it. Forex ships first; equities and crypto come later. | EXT-0189–EXT-0192, EXT-0204 |
| Application flow—event loop, Bot→Book→BMS orchestration, broker sessions, backtest loop, downloads—does not belong in `qmf-core`. | EXT-0095, EXT-0108, EXT-0112 |
| Current operator rulings outrank GitBook, legacy, recovery, wiki/BMAD, research, and assistant-authored tracker/spec text. GitBook is the Book/BMS governance baseline, not a complete mechanics source; old corpora need fresh ratification. | EXT-0040–EXT-0044 |
| Documentation precedes factory code; document QMF first, then the trading node, and let node code wait for its QMF dependencies. | EXT-0075, EXT-0107, EXT-0218, EXT-0227 |
| Documentation must cover the full QMF V1 blueprint, not only the small first brick. | EXT-0235–EXT-0239 |

### Final roster—the late correction must win

| Final component | Required ledger reading | Evidence |
|---|---|---|
| Overall | QMF V1 is **five libraries plus two small modules**. The five hats are a design lens, not package-count law. | EXT-0230, EXT-0244–EXT-0246 |
| `qmf-core` | Accepted first brick: pure domain language/primitives, exact money/time direction, broad nouns, typed refusals, canonical serialization/fingerprints, versioning; no runtime loop/broker/backtest/download. Acceptance does **not** ratify all six pending technical choices. | EXT-0065, EXT-0095, EXT-0112–EXT-0114, EXT-0177, EXT-0191–EXT-0192 |
| `qmf-registry` | Included for identity, lineage, and registration gates. Identity/graph lineage is accepted only in principle; the exact fingerprint/charter/occurrence model, edge catalog, and JSONL schema are study-derived. Look-ahead/causality and attempt-count gates survive here. | EXT-0157–EXT-0159, EXT-0178, EXT-0194–EXT-0197, EXT-0247–EXT-0248 |
| `qmf-data` | Included. Direct live rulings are keep all obtainable history/raw evidence, newest-~12-month sealed holdout, default split discipline, and off-site backup. The exact six-layer schemas and Parquet/DuckDB/SQLite stack remain study/pending-detail material. | EXT-0121–EXT-0122, EXT-0152–EXT-0156, EXT-0198–EXT-0205, EXT-0215–EXT-0222, EXT-0233, EXT-0249 |
| `qmf-indicators` | Included for light/incremental indicators and wrappers; wrapping suitable TA-Lib-class dependencies is directionally agreed. Canonical arithmetic and dual-reference policy are not silently frozen. | EXT-0123–EXT-0125, EXT-0180–EXT-0181, EXT-0250 |
| `qmf-structure` | Included for QMX-owned causal levels/zones/market-structure components; study external ideologies but do not transplant strategy-family code. Detailed families require later depth passes. | EXT-0061–EXT-0062, EXT-0126–EXT-0128, EXT-0251 |
| Venue module | Included as a small Python/cTrader Open API seam, not a standalone library or runtime loop; later crypto/equity venues use the same seam. | EXT-0129, EXT-0141–EXT-0142, EXT-0148, EXT-0241, EXT-0252 |
| Risk module | Included at high level as versioned/updatable Books+BMS V1 with money rules, exits, and correlation concerns; detailed design is blocked on the dedicated node/Book reconciliation. | EXT-0130–EXT-0137, EXT-0160, EXT-0165, EXT-0242, EXT-0253 |

### Live laws crossing components

| Ledger must say | Evidence |
|---|---|
| Signals/Bots do not own money quantity; risk, sizing, and permission live above them in Book/BMS territory. | EXT-0015, EXT-0020, EXT-0067, EXT-0153 |
| Confluence is Levels + Triggers + Confirmations, with variants/nesting and no Exit. A Trigger is the exact trade-entry event. | EXT-0066–EXT-0068, EXT-0164 |
| A Bot may contain multiple confluences; do not preserve the singular formula as settled fact. | EXT-0161 |
| Promotion into live money is human-only; agents run tests and make evidence, but never promote or decide acceptance. A plain-Python Bot may be promoted. | EXT-0146, EXT-0166–EXT-0167 |
| Paper mode is Book-level: the Book moves to paper/demo and its Bots follow; no parallel Bot paper twin; one Bot binds to one Book. This is a recorded ruling whose direct C0022 wording is unavailable. | EXT-0213–EXT-0214 |
| News blackout is pair-scoped and separate from SQS; unaffected pairs may keep trading. The precise ±15-minute timing is less certain than the separation/pair scope. | EXT-0138–EXT-0139, EXT-0223–EXT-0224 |
| SQS means Spread Quality Sensor and is a distinct gate; its formula remains open. | EXT-0069, EXT-0223 |
| Synthetic data may stress scenarios but may never validate an edge; generation is algorithmic, not LLM-based. | EXT-0093 |
| Data acquisition timing is plumbing now, bulk Dukascopy download at first install; standalone calendar forward capture is the exception and not a QMF module. | EXT-0079–EXT-0081, EXT-0216 |
| Definitions/results are content-addressed and versioned; definition changes mint new versions rather than rewrite history. | EXT-0016, EXT-0113–EXT-0114 |
| Architecture is intended for real load around forty Bots, not a toy. The assistant’s “95th percentile” wording is a design interpretation, not an independently stated measured percentile. | EXT-0212, EXT-0231 |
| Code must be human- and agent-readable; modules ship with tests and reference usage; mock data and Bots do not ship. | EXT-0076, EXT-0089–EXT-0090, EXT-0111 |

### Explicit V1 exclusions

| Excluded from QMF V1 | Evidence |
|---|---|
| MIS is a trading-node ML-ensemble component consuming data/indicator capabilities, not a `qmf-mis` library. | EXT-0123, EXT-0180, EXT-0240 |
| Full researcher tooling, backtesting/statistical machinery, and fill/parity design require their own session. Only the causality/look-ahead gate and attempt counter remain in registry. | EXT-0021, EXT-0054–EXT-0056, EXT-0143–EXT-0148, EXT-0168, EXT-0187, EXT-0243, EXT-0247, EXT-0265–EXT-0267 |
| `qml` Bot library is a later consumer; its Bot↔Book binding contract is not designed. | EXT-0068, EXT-0091, EXT-0254 |
| Agent authoring surface, Context/disposer/event bus, and extension plumbing belong to the agentic era. | EXT-0027–EXT-0028, EXT-0036–EXT-0037, EXT-0057–EXT-0058, EXT-0082, EXT-0115, EXT-0163 |
| UI/Simulator is later product scope, not framework foundation. | EXT-0074, EXT-0108 |
| Prop-firm Books/Book creation belong to the agentic-era Book session; no Program/Campaign challenge machinery in V1. | EXT-0059–EXT-0060, EXT-0169–EXT-0170 |

## Explicit deaths and supersession chains

Every row needs a `dead` entry or an explicit supersession chain with the quoted reason—not mere absence.

| Earlier idea | Final disposition | Evidence |
|---|---|---|
| Existing tracker/map as authority | Demoted: explicitly unverified and potentially rebuilt. | EXT-0007 |
| Deterministic runtime “kernel”/one-kernel-two-plugs framing | Superseded by qmf-core definitions plus a separately specified trading node; term retired. Owning domain arithmetic survives. | EXT-0014, EXT-0047–EXT-0053 |
| Three-day engine-adoption spike | Dead: cancelled. | EXT-0051 |
| Third-party strategy-family packages/code transplantation | Dead as product strategy; mental models and permitted wrappers survive. | EXT-0050, EXT-0061–EXT-0062, EXT-0109 |
| Futures/options trading | Permanently out; derived options-style levels are not permission to trade those asset classes. | EXT-0063, EXT-0127 |
| Dimensionally broken `FORM-0006` | Dead as-is; requires a fresh repaired formula if ever reintroduced. | EXT-0071 |
| Universal “one ID card for everything” | Dead as premature abstraction; identity/graph lineage survives only in principle and its study replacement is provisional. | EXT-0157–EXT-0159, EXT-0178, EXT-0194–EXT-0197 |
| Broker Exam / bundled connection+sim-live parity | Dead as bundle; “exam” banned due vocabulary collision. Simple connection survives; parity moves to backtesting. | EXT-0140, EXT-0143–EXT-0148, EXT-0265 |
| Agent page as immediate spine | Deferred until the framework and documentation exist; not a V1 authoring contract. | EXT-0163 |
| Answer-key catalog as ratified spine | Not ratified; later catalog remains study evidence. | EXT-0179, EXT-0193, EXT-0203 |
| Program/Campaign prop-challenge machine | Dead/off; prop firm is a later Book. | EXT-0060, EXT-0169–EXT-0170 |
| `qmf-mis` library | Superseded by node-owned MIS consuming `qmf-data`/`qmf-indicators`. | EXT-0123, EXT-0180, EXT-0240 |
| Standalone trader/`qmf-broker` library | Narrowed to a small venue module. | EXT-0148, EXT-0241, EXT-0252 |
| Full `qmf-risk` library in the early hat roster | Narrowed to versioned/updatable risk module, detailed later. | EXT-0242, EXT-0253 |
| `qmf-experiment`/backtesting in V1 | Deferred out; only two registration gates retained in registry. | EXT-0168, EXT-0243, EXT-0247 |
| Bot-level continuous paper twin / one Bot paper while Book stays live | Dead; paper mode is Book-level. Direct original wording is hidden by the C0022 collapse. | EXT-0201, EXT-0213–EXT-0214 |
| Special paper simulation through news blackout | Dead: ordinary recorders continue, so the special simulation was dropped. | EXT-0186, EXT-0234 |
| Graph database/Neo4j requirement | Dead for V1; graph-shaped lineage does not imply a graph database. Exact persistence format is still open. | EXT-0158, EXT-0182, EXT-0200, EXT-0228 |
| “Minimal core” as the overall deliverable name | Dead/retired; final name is QMF V1 Blueprint. | EXT-0235–EXT-0237 |
| `plugins`, backtesting `engine`, `exam`, and fake-counterparty vocabulary | Banned/retired terms with collision or framing reasons. | EXT-0074, EXT-0077, EXT-0140, EXT-0184 |
| DPR/PRS as recovered authority | Dead/do-not-revive legacy mechanisms; redemption loop is history, not live behavior. | EXT-0256–EXT-0260 |
| Recovering old alpha-decay math | Dead: two sources indicate it was never written; design fresh. | EXT-0264, EXT-0270 |

## Conflicts and status traps that must remain visible

| Trap | Correct ledger treatment | Evidence |
|---|---|---|
| Bot = one confluence vs multiple confluences | Conflict/open gap; later direct wording favors `1..n`, but obtain explicit confirmation before a binding schema. | EXT-0068, EXT-0161 |
| Exit ownership | QMX2 repeatedly puts exit/sizing/risk in Book territory, while legacy baseline contains Bot exit organs. Keep outside qmf-core and route to the risk/node session; do not “resolve” from assistant prose. | EXT-0020, EXT-0067, EXT-0135–EXT-0137, EXT-0153, EXT-0165 |
| QMF data contracts vs app-owned acquisition lifecycle | Likely seam: QMF supplies reusable contracts/adapters, app owns scheduling/download lifecycle. Mark conflict/open until ratified. | EXT-0079–EXT-0081, EXT-0095, EXT-0249 |
| Build-own vs external dependencies | Live reading is own contracts/domain semantics and no transplantation, while suitable dependency wrappers are allowed. Exact licence/allowlist remains a gap. | EXT-0047–EXT-0052, EXT-0061–EXT-0062, EXT-0109, EXT-0250 |
| Registry included vs exact registry model ratified | Include component, but keep fingerprint/charter/occurrence kinds, edge catalog, `definition: opaque`, and JSONL format provisional/study-backed. | EXT-0178, EXT-0194–EXT-0197, EXT-0200, EXT-0248 |
| Data included vs six-layer/storage design ratified | Include component and direct retention/holdout laws; keep exact L0–L5 schemas, twelve streams, Parquet/DuckDB/SQLite, and ArcticDB rejection out of ratified contract until Stage 4. | EXT-0156, EXT-0198–EXT-0205, EXT-0249 |
| TA-Lib wrapper direction vs canonical arithmetic | Wrapping is directionally agreed; TA-Lib as the sole canonical oracle is one of the pending frozen choices. | EXT-0097–EXT-0099, EXT-0250 |
| Latest twelve months | It is a sealed holdout, not the total dataset. Retain all source history. The exact “one look” mechanics need explicit contract wording. | EXT-0219–EXT-0222, EXT-0233 |
| Pair-scoped news gate vs ±15 timing | Pair scope/separation from SQS is strong; the operator said “I think/believe” about ±15, so keep the number provisional unless Stage 4 confirms it. | EXT-0138–EXT-0139, EXT-0223–EXT-0224 |
| Paper-mode/one-Bot-one-Book evidence | Preserve the recorded ruling but annotate that its direct answer was lost in C0022 export collapse. | EXT-0213–EXT-0214 |
| “95th percentile” | Direct evidence is “around 40-something Bots”; the percentile label is assistant normalization. Do not fabricate a formal percentile SLO. | EXT-0212, EXT-0231 |
| Multiple BMSs/crypto-specific BMS | Possible future, not a V1 multiplicity requirement. | EXT-0132, EXT-0209, EXT-0242 |
| Calendar/tick urgency | Calendar capture is the explicit standalone exception; live tick necessity was delegated/uncertain and later blocked on broker access with Dukascopy backfill. | EXT-0018, EXT-0031–EXT-0034, EXT-0080–EXT-0081 |

## Numeric and enumerated values—registry audit

Each value must be either a registry entry linked to a decision, an operational fact, or explicitly provisional. Do not mix these classes.

| Value | Class/status | Evidence |
|---|---|---|
| QMF estimate: **100–150 factory-days** | Assistant estimate/context, not delivery commitment. | EXT-0023 |
| Agentic prerequisites: **~5 research papers** | Scope context, not a framework feature. | EXT-0057 |
| Rebuild ambition: **at most ~2/year** | Design-value target, not measured SLO. | EXT-0110 |
| Deployment shape: **2 deployables** (QMX app + one trading VPS) | Earlier foundation decision; ensure it does not leak process lifecycle into qmf-core. | EXT-0084 |
| ML training: **~quarterly** | Node/MLOps context outside QMF V1. | EXT-0085 |
| Pending fidelity enum: `bar_close / intrabar / tick` | **Unratified frozen choice.** | EXT-0097–EXT-0098 |
| Pending clock: **UTC nanoseconds** | **Unratified frozen choice.** | EXT-0097, EXT-0099 |
| Pending instrument identity: `(venue, symbol)` with opaque symbol | **Unratified frozen choice.** | EXT-0097, EXT-0100 |
| Pending strategy bar `SR*` and result-key tuple | **Unratified frozen choices.** | EXT-0097, EXT-0101 |
| `R` = one unit of original pre-trade risk | Vocabulary/value; risk contract still later. | EXT-0070 |
| FX clock facts: **5pm New York rollover**, weekend/week boundary, **triple-swap Wednesday**, DST desync | Domain input requiring exact calendar contract; swap-free financing means admin fee, not swap. | EXT-0103–EXT-0104 |
| Data holdout: newest **~12 months** | Directly selected direction; precise seal/access mechanics need contract/Stage 4 confirmation. | EXT-0220, EXT-0233 |
| News blackout: **15 minutes before/after** | Provisional due operator’s “I think/believe” wording. | EXT-0224 |
| Expected load: **around 40 Bots** | Real design case. Do not turn “95th percentile” into a measured SLO without evidence. | EXT-0212, EXT-0231 |
| Final roster: **5 libraries + 2 modules** | Strong late correction; must be exact. | EXT-0244–EXT-0246 |
| Data blueprint: **6 layers** | Component direction only; exact layers still need definition/ratification. | EXT-0198, EXT-0205 |
| Demo accounts: **2 roles** | Recorded ruling via collapsed-answer recap; evidence caveat. | EXT-0232 |
| Recorder schedule: **06:00 and 18:00 daily** | Operational fact, not library API. | EXT-0173 |
| Recorder first snapshot: **96 events, 8 high-impact** | Ephemeral operational observation. | EXT-0172 |
| Feed cap: **~2 downloads/5 minutes** | External operational constraint. | EXT-0174 |
| Baseline bench: **2 consecutive stop-outs**, rest of day, reset next open | Trading-node/risk input; blocked until “stop-out” is defined. | EXT-0259, EXT-0261 |
| Legacy PRS: **6 weights → 0–100 → 3 tiers**; DPR: **rolling 10-day tier** | Dead legacy evidence; never populate live registry variables from it. | EXT-0256–EXT-0258 |

## Required gaps before code-facing documentation

### Cross-cutting blockers

- Confirm all six pending frozen choices: fidelity enum, canonical indicator arithmetic, UTC/time precision, instrument identity, `SR*`, and result-key tuple. [EXT-0097–EXT-0101, EXT-0177]
- State one dependency/licence law distinguishing permitted wrappers from prohibited code/contract transplantation. [EXT-0047–EXT-0052, EXT-0061–EXT-0062, EXT-0109]
- Confirm Bot confluence cardinality (`1..n` recommended from later direct wording). [EXT-0068, EXT-0161]
- Ratify the data/acquisition seam between reusable QMF mechanisms and app-owned scheduling/lifecycle. [EXT-0079–EXT-0081, EXT-0095, EXT-0249]
- Mark C0022-derived rulings explicitly and ask whether Book-level paper mode, one-Bot/one-Book, full raw retention, and demo-account roles stand exactly as restated. [EXT-0213–EXT-0216, EXT-0232]

### `qmf-core`

- Money precision, currency representation, rounding/quantization, and arithmetic failure behavior. [EXT-0065]
- Exact clock/timezone/trading-day/session/calendar contracts across Forex, crypto, and equities. [EXT-0065, EXT-0103–EXT-0104, EXT-0192]
- Asset-neutral instrument/symbol/order-flow nouns and identity. [EXT-0065, EXT-0100, EXT-0126–EXT-0128]
- Canonical serialization, fingerprint evolution, collision/version rules, typed refusal taxonomy, and compatibility/deprecation policy. [EXT-0113–EXT-0114, EXT-0110–EXT-0111]

### `qmf-registry`

- Exact kind catalog and identifier shape; charter amendment/countersignature; occurrence identity; Bot career/revision/variant semantics. [EXT-0194–EXT-0197]
- Typed lineage edges, acyclicity/transaction rules, and persistence format. “No graph DB” is settled direction; JSONL is still a study proposal. [EXT-0158, EXT-0182, EXT-0200, EXT-0228]
- Causality-test inputs/output/refusal contract and attempt-counter scope/reset/budget semantics. [EXT-0247–EXT-0248]

### `qmf-data`

- Ratify or replace the six layers and define each layer’s schemas, ownership, valid-time/known-time behavior, and access rules. [EXT-0017, EXT-0152–EXT-0156, EXT-0198–EXT-0205]
- Split/holdout registry: training/research/out-of-sample assignment, newest-year seal, one-look logging, and whether live performance data can train MIS. [EXT-0122, EXT-0219–EXT-0222, EXT-0233]
- Journal stream list, fields, cadence, quantity, duration, retention, and component ownership for Bot/Book/BMS/MIS/SQS/kill switch. [EXT-0154–EXT-0155]
- Ratify stores rather than inheriting Parquet/DuckDB/SQLite and ArcticDB rejection from a study. Define migrations, backup restore verification, and legal posture for archived feeds. [EXT-0094, EXT-0156, EXT-0176, EXT-0199, EXT-0217]
- Decide live tick capture necessity/retention once broker access exists; preserve calendar feed limitation (no actual values, so no surprise strategy). [EXT-0034, EXT-0081, EXT-0175]

### `qmf-indicators` and `qmf-structure`

- Define the light/heavy boundary, incremental protocol, warmup/stability metadata, versioning, replay equivalence, and whether TA-Lib is canonical or merely wrapped. [EXT-0099, EXT-0123–EXT-0125, EXT-0180–EXT-0181, EXT-0250]
- Define each causal Level/Zone/Trigger/Confirmation family and its look-ahead proof; avoid a closed assistant-generated taxonomy. [EXT-0066, EXT-0126–EXT-0128, EXT-0164, EXT-0251]

### Venue module

- Spotware/Open API application status and approval dependency. [EXT-0019]
- Port/capability contract, authentication/OAuth/secret rotation, token expiry, VPS failure/position flattening, and outage behavior. [EXT-0102, EXT-0105, EXT-0252]
- Confirm cTrader trendbar BID-vs-mid basis, tick semantics/retention, rate limits, idempotency, reconciliation, and error/refusal behavior. [EXT-0106, EXT-0129]

### Risk module / future trading-node reconciliation

- Extract and operator-verify the Book schema; do not infer it from assistant summaries. [EXT-0135, EXT-0160, EXT-0165]
- Resolve exit ownership and define fast invalidation, dynamic SL/TP, correlation ledger, money variables/default/editability, same-tick priority, and BMS version/plurality. [EXT-0020, EXT-0132, EXT-0135–EXT-0137]
- Specify Book-level live↔paper transition, account binding, result continuity, and interaction with news/SQS/daily-limit conditions. [EXT-0149–EXT-0151, EXT-0213–EXT-0214, EXT-0223–EXT-0224]
- Define kill-switch behavior when the broker is down. [EXT-0102]
- Define “stop-out,” resolve overloaded symbol `B`, decide the one canonical BENCHED namespace, and design alpha-decay math fresh. Do not revive DPR/PRS. [EXT-0255–EXT-0270]

### Explicitly deferred gaps—not V1 blockers

- Bot↔Book binding contract and QML package design. [EXT-0068, EXT-0091, EXT-0254]
- Fill model, sim/live parity, Book testing matrix mechanics, overfitting battery, and backtesting framework. [EXT-0054–EXT-0056, EXT-0064, EXT-0143–EXT-0148, EXT-0168, EXT-0265–EXT-0267]
- Agent surface/harness and UI/Simulator. [EXT-0057–EXT-0058, EXT-0074, EXT-0082, EXT-0115, EXT-0163]
- Prop-firm Book mechanics and Book creation. [EXT-0059–EXT-0060, EXT-0169–EXT-0170]

## Ledger-writer failure modes to check explicitly

- [ ] Final roster is exactly five libraries plus venue/risk modules; no `qmf-mis`, `qmf-experiment`, `qmf-broker`, full `qmf-risk` library, QML, or agent surface resurrected.
- [ ] qmf-core acceptance does not silently ratify the six frozen values.
- [ ] Registry/data detail is not labeled ratified merely because the components are in the roster.
- [ ] Every killed idea has a reason and, where it once held, a supersession link.
- [ ] C0022-derived rulings carry the collapsed-source evidence caveat.
- [ ] Bot cardinality, exit ownership, acquisition seam, and dependency policy remain conflict/open rather than being agent-resolved.
- [ ] “Around forty Bots” is not rewritten as a measured 95th-percentile performance SLO.
- [ ] ±15-minute news timing remains provisional unless Stage 4 explicitly confirms it.
- [ ] Legacy PRS/DPR values never enter the live variable registry.
- [ ] Backtesting, QML, agentic, UI, prop-firm, and detailed risk/node work stay out of V1 contracts except for neutral primitives and named registry gates.
