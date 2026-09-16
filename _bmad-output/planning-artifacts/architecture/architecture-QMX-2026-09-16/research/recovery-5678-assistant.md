# 20260826_180446_36307b msg 5678 role=assistant compacted=0

# STRATS design-decision recovery

Citation key:

- `FG M#` = message ID from session `20260824_121737_86f88c` (“Friendly Greeting”).
- `GM M#` = message ID from session `20260825_115530_94412f` (“Continue STRATS Forex context library”).
- “Settled” means repeatedly endorsed or explicitly reaffirmed.
- “Proposed” means discussed in detail but not finally ratified.
- “Rejected/superseded” means a later user correction displaced it.

## 1. Executive conclusion

The two sessions establish a strong semantic design, but they do not establish a final physical folder tree or rigid schema.

The durable design is:

```text
heterogeneous sources
→ source-faithful evidence and atomic claims
→ reusable, role-neutral primitive dictionary
→ strategy-specific role bindings
→ Boolean/temporal/stateful strategy logic graph
→ human- and agent-readable strategy package
→ lineage, catalog, mini-KBs
→ later downstream implementation/testing by QMX or another consumer
```

The controlling correction is:

> STRATS is a portable plain-file/Obsidian knowledge library—“just a folder,” not a software system.

`[GM M4067; GM M4070; also the late Friendly Greeting correction around FG M2607]`

Therefore:

- Bots, models, scripts, Gemini, NotebookLM, n8n, Firecrawl, and other tools may help construct and populate STRATS.
- None of them should be runtime dependencies of the finished library.
- QMX does not dictate the current STRATS layout. QMX should adapt to the portable library later.
- No database, adapter, test harness, package lock, executor, run ledger, or promotion framework is part of the presently accepted STRATS core.
- The dictionary/role/graph semantics are settled.
- Exact directory names, serialization, package filenames, mini-KB taxonomy, and several classification axes remain open.
- The library was discussed extensively but was not canonically populated at the point of `GM M4070`.
- The post-compaction dictionary worker campaign did not settle the design and was frozen as a regression.

---

# 2. Mission, scope, and system boundary

## 2.1 STRATS’s purpose

STRATS is intended to:

- collect trading material from videos, books, papers, social media, websites, code, and existing corpora;
- preserve source evidence and uncertainty;
- split reusable “organs” or concepts out of complete strategies;
- turn discretionary explanations into structured, codable candidate specifications;
- create strategy packages, variants, composites, and lineage;
- build focused mini knowledge bases;
- be browsable in Obsidian and readable as ordinary files;
- front-load substantial strategy research before QMX is ready.

This originated in the first user brief. `[FG M769]`

The final product is not a sample or skeleton. It is eventually meant to become a substantially populated knowledge library. Public playlists, channels, topics, and notebooks are discovery seeds rather than exhaustive corpora.

## 2.2 Portability

Settled:

- STRATS lives at `C:/Users/Mubarak/Desktop/Stats`.
- It must remain usable without Hermes, n8n, Gemini, NotebookLM, Firecrawl, or QMX.
- Hermes agents and external tools are construction machinery only.
- Markdown/plain files and Obsidian-style links are the intended interaction surface.
- A small amount of YAML/front matter or structured sidecar data was contemplated, but no exact format was ratified.
- Python/reference implementations may help define technical-analysis semantics, but STRATS itself is not a Python application.

`[FG M795, M796, M831; GM M4065–M4070]`

## 2.3 Market and horizon scope

Evolution:

- Friendly Greeting treated Forex as primary, with scalping and intraday/day trading primary, swing allowed, and position trading/futures execution out of immediate scope.
- The current recovered scope includes Forex and crypto spot.
- Futures, equities, and derivative-market sources may still contribute transferable concepts, but their market origin, venue/data assumptions, and transfer caveats must remain explicit.
- Centralized volume, DOM, futures-session, exchange-order-book, funding, and broker-feed information must never be silently translated into spot FX or spot crypto semantics.

## 2.4 QMX boundary

The boundary evolved substantially.

### Early Friendly Greeting proposal

The assistant initially proposed that strategy packages might include:

- experiment manifests;
- evaluations/results;
- QMX bindings;
- a QMX adapter;
- book-conditioned overlays;
- execution and certification artifacts.

`[FG M941 and the strategy-package subagent response around FG M974]`

### User correction and Gold Mine result

These were moved out of STRATS:

- executable test manifests;
- run results;
- experiment ledgers;
- executors;
- optimization/evolution machinery;
- certification state;
- package/runtime locks;
- QMX book/admission/sizing/breaker policy;
- live account state;
- QMX adapters;
- runtime intelligence and memory.

The Git-worktree analogy was about downstream isolated experimentation, not a reason to put Git worktrees or experiment infrastructure inside STRATS.

Settled Gold Mine rule:

> QMX will adapt to the library later; STRATS does not need to be designed around a current QMX adapter.

`[GM M4066, M4067, M4070]`

STRATS can still preserve:

- source-native risk ideas;
- source-defined stops and exits;
- source claims about performance;
- hypotheses and questions requiring later testing.

But those are research facts, not QMX runtime machinery or proof of edge.

---

# 3. Folder layouts discussed, and how they evolved

## 3.1 Friendly Greeting visual tree

The first important visual tree was given in `FG M941`:

```text
STRATS/
├── sources/                         # Immutable source evidence
│   ├── videos/
│   ├── books/
│   ├── papers/
│   ├── websites/
│   └── social/
│
├── dictionary/
│   ├── primitives/                  # WHAT EXISTS
│   │   ├── patterns/
│   │   │   └── bullish-engulfing.md
│   │   ├── indicators/
│   │   │   └── rsi.md
│   │   ├── market-structure/
│   │   ├── liquidity/
│   │   ├── order-flow/
│   │   └── time-and-sessions/
│   │
│   └── bindings/                    # HOW A PRIMITIVE IS USED
│       ├── level/
│       ├── trigger/
│       ├── confirmation/
│       └── exit/
│
├── knowledge/                       # Mini knowledge bases
│   ├── pairs/
│   │   ├── eurusd/
│   │   └── gbpusd/
│   ├── sessions/
│   │   ├── london/
│   │   └── new-york/
│   ├── methodologies/
│   │   ├── smc/
│   │   ├── ict/
│   │   └── order-flow/
│   ├── macro/
│   ├── prop-firms/
│   ├── scalping/
│   └── swing-trading/
│
├── strategies/
│   └── asian-sweep-reversal/
│       ├── manifest.yaml            # Identity, scope, status
│       ├── evidence/                # Exact source claims and frames
│       ├── graph.yaml               # Strategy relationships
│       ├── lineage.yaml             # Parents, children, combinations
│       ├── variants/                # Overlays, not full copies
│       ├── experiments/             # What agents must test
│       └── evaluations/             # QMX/QMF results
│
├── intelligence/                    # Dated changing market context
│   ├── pair-snapshots/
│   ├── correlations/
│   ├── macro-regimes/
│   └── session-conditions/
│
└── adapters/
    └── qmx/
```

### Status of this tree

The user reacted positively to the visual shape—“I’m liking it”—and especially to the dictionary reuse, package, and lineage ideas. `[FG M975]`

However, this was not a final line-by-line approval. Later corrections changed it:

- `experiments/` and `evaluations/` moved downstream.
- `intelligence/` was rejected as a STRATS responsibility because it represented mutable/live state.
- `adapters/qmx/` was no longer needed.
- Fixed role directories under `dictionary/bindings/` became questionable because most bindings are strategy-specific.
- `scalping/` and `swing-trading/` were recognized as cross-cutting style/horizon axes rather than equivalent to methodologies.
- Macro’s relationship to methodologies remained unsettled.
- The source branch was too narrow.

## 3.2 Software-heavy package tree proposed by a Friendly Greeting subagent

A strategy-package specialist proposed this alternate tree:

```text
forex-context/
├─ schemas/
│  ├─ primitive.schema.yaml
│  ├─ strategy-package.schema.yaml
│  ├─ graph.schema.yaml
│  ├─ overlay.schema.yaml
│  ├─ test-manifest.schema.yaml
│  └─ result-envelope.schema.yaml
│
├─ primitives/
│  └─ <primitive-id>/<version>/
│     └─ primitive.yaml
│
├─ evidence/
│  ├─ sources/<source-id>/manifest.yaml
│  └─ claims/<claim-id>.yaml
│
├─ strategies/
│  ├─ <strategy-id>/
│  │  ├─ package.yaml
│  │  ├─ package.lock.yaml
│  │  ├─ baseline/
│  │  │  ├─ candidate.yaml
│  │  │  ├─ bindings.yaml
│  │  │  └─ graph.yaml
│  │  ├─ overlays/
│  │  │  └─ <overlay-id>.yaml
│  │  ├─ candidates/
│  │  │  └─ <candidate-node-id>.yaml
│  │  ├─ evidence/
│  │  │  ├─ claim-map.yaml
│  │  │  └─ assumptions.yaml
│  │  ├─ tests/
│  │  │  └─ <test-manifest-id>.yaml
│  │  └─ results/
│  │     ├─ index.ndjson
│  │     └─ runs/<run-id>.yaml
│  │
│  └─ <combined-strategy-id>/
│     ├─ package.yaml
│     ├─ package.lock.yaml
│     ├─ composition.yaml
│     ├─ candidates/
│     ├─ tests/
│     └─ results/
│
├─ lineage/
│  ├─ nodes.ndjson
│  └─ edges.ndjson
│
└─ catalog/
   ├─ primitives.yaml
   └─ strategies.yaml
```

### Status of this tree

This was a specialist proposal, not an agreed STRATS layout.

Useful concepts retained:

- one strategy can own a folder;
- baseline versus variants/composites;
- evidence links;
- explicit lineage;
- catalog/index;
- overlays/diffs instead of copied packages.

Superseded or rejected for current STRATS:

- schema-first architecture;
- lockfiles;
- tests and result envelopes;
- run ledgers;
- QMX-specific reproducibility machinery;
- software-package semantics.

`[FG subagent output around M974; revised by GM M4066–M4070]`

## 3.3 Gold Mine lean candidate tree

The Gold Mine recovery preserved this leaner candidate:

```text
STRATS/
├── sources/
│   ├── creators/
│   ├── channels/
│   ├── playlists/
│   ├── videos/
│   └── evidence/
├── primitives/
├── strategies/
│   ├── source-strategies/
│   ├── entry-hypotheses/
│   ├── fragments/
│   └── relationships/
├── knowledge/
│   ├── pairs/
│   ├── sessions/
│   ├── methodologies/
│   ├── concepts/
│   ├── styles/
│   ├── execution-archetypes/
│   └── prop-firms/
├── lineage/
└── catalog/
```

### Status of this tree

It captured the corrected direction but was never approved or created.

Known problems still requiring resolution:

- `dictionary/` versus `primitives/` was unresolved.
- `entry-hypotheses/` could force a classification that should remain optional.
- `execution-archetypes/` was provisional terminology.
- `macro/` was missing despite being discussed.
- The source branch omitted podcasts, books, papers, articles, websites, social posts, code, MQL5, and TradingView.
- Mini-KBs for patterns, indicators, liquidity/order flow, risk/exits, and creator terminology were absent.
- No dictionary family layout had been approved.
- No individual strategy-folder interior had been approved.
- `lineage/` and `strategies/relationships/` might duplicate each other.

## 3.4 Final folder-layout verdict

A physical tree was discussed repeatedly and accepted in spirit, but no final tree was ratified.

Settled structural areas:

```text
sources/evidence
dictionary/primitives
strategies/packages
knowledge/mini-KBs
lineage
catalog/indexes
```

Open physical choices:

- exact root names;
- source hierarchy versus tag/backlink navigation;
- global versus per-strategy bindings;
- strategy class folders versus tags;
- methodology/macro/style placement;
- dedicated lineage folder versus package-local lineage plus indexes;
- exact contents and filenames in a strategy folder;
- Markdown versus YAML/front matter division.

At the end of the Gold Mine recovery, the intended next design action was to show Mubarak a corrected empty-folder tree, including one strategy folder’s interior, before creating or populating it.

---

# 4. What a strategy specification/package contains

## 4.1 The core answer

A complete strategy is not “exactly four fields.” It is a potentially unbounded collection of reusable concepts connected through explicit logic, timing, scope, and evidence.

The strongest recovered minimum is:

### 1. Identity and classification

- stable candidate/strategy ID;
- title and short human-readable summary;
- version/status;
- source-native strategy, partial setup, descriptive pattern, entry-only hypothesis, derived variant, or composite;
- source/creator identity;
- target market and holding horizon.

### 2. Source and evidence map

- source IDs and canonical locators;
- exact quotations;
- timestamps, pages, frame IDs, OCR regions, chart references;
- claim-to-rule links;
- whether each item was:
  - explicitly spoken/written;
  - visually demonstrated;
  - inferred;
  - standardized/added by STRATS;
  - unresolved.

### 3. Scope and context

- asset class, instrument/pair, and venue/feed;
- direction;
- setup timeframe and execution timeframe;
- session and timezone;
- market regime;
- spread, volatility, liquidity, news/event, or data-health constraints;
- source-market and target-market transfer assumptions.

### 4. Primitive references

- stable references to canonical dictionary entries or profiles;
- no repeated redefinition of common concepts;
- parameter values and their provenance.

### 5. Candidate-specific role bindings

For each primitive:

- job/role in this strategy;
- selected parameter/profile;
- pair, timeframe, session, direction;
- pre-trigger, synchronous, or post-trigger timing;
- bar-close versus intrabar evaluation;
- dependencies and graph relations;
- evidence and data provenance;
- unknown or ambiguous values.

### 6. Setup/location/eligibility logic

- where or under what conditions the strategy becomes relevant;
- location construction and lifecycle;
- context filters, gates, scores, vetoes, or regime labels;
- prerequisites and arming conditions.

### 7. Trigger, confirmation, and entry semantics

- trigger event or state transition;
- compound trigger expression where applicable;
- pre-trigger filters;
- synchronous and delayed confirmations;
- explicit entry action;
- market/limit/stop behavior;
- price basis;
- delay, timeout, expiry, reset, cooldown, and re-entry.

### 8. Invalidation, stop, target, exit, and management

- setup/thesis invalidation;
- level invalidation;
- source-defined stop;
- targets and exit events;
- partial exits, trailing, break-even, time exits, session close, reversal exits;
- open-trade management;
- explicit statement when any of these are missing.

Important evolution:

- Friendly Greeting strongly endorsed the term `entry_hypothesis` for an entry mechanism with no exit. `[FG M795, M796]`
- Gold Mine retained the need to expose missing exits but softened the universal classification rule: do not silently invent an exit, but do not force every incomplete source into one rigid folder/type. `[GM M4070]`

### 9. Operational logic graph

- nodes for bound primitives, states, conditions, and actions;
- Boolean, temporal, state, and execution relationships;
- long/short asymmetry;
- alternative branches;
- reset and lifecycle semantics.

### 10. Parameters and defaults

Every threshold/default should say whether it is:

- source-stated;
- visually inferred;
- taken from a cited reference implementation;
- a STRATS standard/profile;
- generated for future experimentation;
- unresolved.

A dictionary default is not automatically the source’s default.

### 11. Dependencies and assumptions

- required price/volume/order-flow/news data;
- indicator/labeler assumptions;
- broker/venue dependencies;
- bar construction and timezone assumptions;
- latency and transaction-cost sensitivity;
- visual ambiguities or unavailable data.

### 12. Unknowns and conflicts

- missing thresholds;
- unclear timing;
- unreadable chart values;
- ambiguous direction/order type;
- transcript-versus-chart conflict;
- contradiction among source examples;
- unresolved exits or management.

### 13. Lineage and composition

- baseline/source parent;
- child and variant relationships;
- composite parents;
- changed components and semantic diff;
- inherited versus newly required evidence;
- source-defined versus agent-generated changes.

### 14. Research status

- no claim of edge merely because the strategy is clear or codable;
- claimed performance kept as a cited source claim;
- downstream empirical results remain separate;
- transfer and testing status remain separate from source truth.

`[FG M795, M831, M941, M975; GM M4065–M4070]`

## 4.2 Proposed physical split inside a strategy folder

The accepted direction was a small folder, not one giant YAML document.

Strongly supported contents:

```text
<strategy>/
├── README.md or overview
├── identity/manifest information
├── evidence/
├── primitive references and bindings
├── logic/graph
├── assumptions-and-unknowns
├── exits-and-management status
├── lineage/
└── variants or relationships
```

Exact names and extensions remained open.

Early proposed but later removed from STRATS:

- executable experiment manifest;
- evaluation report;
- QMX binding;
- tests;
- run results;
- package lock;
- executor/runtime fields.

---

# 5. Dictionary design

## 5.1 Purpose

The dictionary is a canonical reusable trading language.

The user explicitly liked the ability to write “bullish engulfing” in a strategy and link to one rich definition instead of making every agent rewrite long prose. `[FG M975; GM M4065–M4066]`

It is not:

- a list of only levels, triggers, confirmations, and exits;
- a fixed starter vocabulary;
- a role taxonomy;
- a set of strategy-specific parameter values;
- a claim that each concept is profitable.

## 5.2 Creation method

The intended method combines top-down and bottom-up growth:

1. Domain specialists survey the trading concept space broadly.
2. Seed broad concept families rather than only terms appearing in the first source.
3. Use sources, standards, papers, code, and indicator implementations to define operational semantics.
4. Normalize aliases, creator terminology, marketing names, and spelling variants to canonical entries.
5. Preserve disagreements or materially different definitions as profiles/variants rather than silently merging them.
6. Keep the concept role-neutral.
7. Store strategy-specific roles, values, scope, and timing in bindings.
8. Grow the dictionary as sources expose new concepts and definitions.
9. Cross-link compatible, contradictory, derived, and related concepts.
10. Leave weakly evidenced entries marked as ontology seeds or unresolved rather than pretending they are established facts.

No finite “complete dictionary” was approved. The short lists were explicitly examples only.

## 5.3 Proposed dictionary-entry fields

These were discussed as useful requirements, although exact field names and serialization were not fully ratified:

- canonical ID/name;
- aliases, abbreviations, creator names, and marketing names;
- concept family;
- concise definition;
- semantic boundaries and non-examples;
- observable inputs and outputs;
- data requirements and provenance;
- recognition/detection semantics;
- candidate reference algorithms;
- available indicator/code implementations;
- parameters, units, profiles, ranges, and defaults;
- provenance for every default;
- eligible roles;
- timing/timeframe/lifecycle behavior;
- market/instrument/venue compatibility;
- transfer assumptions;
- compatible concepts;
- incompatible or contradictory concepts;
- redundancies/equivalences;
- parent/child, generalized/specialized, or derived relationships;
- latency/cost/spread sensitivity;
- failure modes;
- uncertainty and known variants;
- exact evidence/citations;
- evidence maturity/status.

The old proposed “QMX/MIS mapping” field became unnecessary once QMX was left out.

## 5.4 How entries connect

Dictionary entries can relate through:

- alias-of;
- equivalent-to;
- broader-than/narrower-than;
- specialization/profile-of;
- derived-from;
- constructed-from;
- depends-on;
- compatible-with;
- incompatible-with;
- often-composed-with;
- contradicts;
- replaces/supersedes.

Strategies do not copy those definitions. Their bindings reference stable dictionary IDs.

Mini-KBs can discuss literature, disagreements, examples, and methodology-specific use without replacing the canonical operational definition.

## 5.5 Conceptual family coverage

These are coverage families, not approved directories and not permanent roles.

### Locations, structures, and level construction

- swing highs/lows;
- support/resistance;
- supply/demand;
- order, breaker, and mitigation blocks;
- fair-value gaps and imbalances;
- equal highs/lows and liquidity pools;
- previous day/week/month and session OHLC/ranges;
- opening ranges and gaps;
- round numbers, pivots, Fibonacci levels;
- moving averages;
- VWAP and anchored VWAP;
- channels, envelopes, ATR bands;
- volume-profile POC/VAH/VAL and high/low-volume nodes;
- pattern boundaries/necklines;
- event-anchored references.

### Trigger events and transitions

- touch;
- rejection;
- close-through;
- breakout;
- failed breakout;
- retest;
- sweep and reclaim;
- displacement;
- break of structure/CHoCH/market-structure shift;
- candlestick completion;
- indicator crossovers, thresholds, and divergence;
- momentum/volatility expansion;
- volume spike;
- order-flow imbalance;
- ordered events such as sweep → displacement → retracement.

### Context, filters, and confirmations

- higher-timeframe bias and structure;
- momentum;
- volatility;
- volume and profile;
- order flow;
- session/time/calendar;
- spread and costs;
- liquidity;
- news/event conditions;
- data health;
- intermarket relationships;
- currency exposure/correlation;
- pair relationships;
- market regime;
- pattern quality;
- distance-to-target and viability constraints;
- hard gates, vetoes, scores, and ranking signals;
- pre-trigger, synchronous, and post-trigger confirmation.

### Invalidation, exit, execution, and management

- thesis/setup invalidation;
- level invalidation;
- fixed, structural, volatility, and time stops;
- opposing-level exits;
- fixed-R targets;
- trailing and break-even;
- partial exits;
- signal reversal;
- session-close exits;
- MAE/MFE rules;
- volatility collapse;
- liquidity targets;
- order type and entry timing;
- pending-order lifecycle;
- cooldown and re-entry.

### Other cross-cutting families

- candlestick and chart patterns;
- indicators and technical transforms;
- liquidity, volume, profile, DOM, and order flow;
- time/session/calendar concepts;
- macro and fundamental events;
- sentiment and positioning;
- cross-market/intermarket context;
- market/data/venue provenance;
- source-native risk and sizing ideas.

`[FG M831; GM M4065–M4066]`

---

# 6. Primitive, role binding, and graph model

## 6.1 The three layers

Settled:

```text
Primitive dictionary
“What reusable thing exists?”

→ Contextual role binding
“What job does it perform in this strategy?”

→ Strategy logic graph
“How do the bound components interact?”
```

`[FG M831; positively received in FG M902 and M975; reaffirmed GM M4070]`

## 6.2 Primitive role flexibility

Examples explicitly used:

- **Bullish engulfing**
  - may trigger an entry;
  - confirm a prior sweep;
  - help construct a future zone/location;
  - contribute to exiting a short.

- **RSI**
  - may trigger;
  - confirm;
  - filter a regime;
  - veto a setup;
  - signal exit.

- **DOM/order flow**
  - may trigger;
  - confirm;
  - act as a liquidity filter;
  - help construct a reference area;
  - but must retain venue/feed provenance.

The primitive’s identity must not be conflated with its role.

## 6.3 Role bindings

A binding carries strategy-specific details:

- role;
- selected profile and parameters;
- pair/instrument;
- timeframe;
- session/timezone;
- direction;
- timing relative to trigger;
- bar-close/intrabar evaluation;
- graph dependencies;
- evidence;
- data provenance;
- ambiguity.

Most bindings are likely strategy-specific. Whether some reusable binding templates should exist globally remained open.

## 6.4 Roles and semantic distinctions

### Location/level

A price reference, area, or structure at which logic is evaluated.

- “London session” or “H1” is context/coordinate, not a level.
- “London-session high” is a level.

### Context/filter

Determines whether a setup is eligible.

Can act as:

- gate;
- veto;
- score;
- ranking feature;
- regime/context label.

It must not be silently merged with chart location.

### Trigger

An event or transition that arms or authorizes entry.

It may be compound and should specify:

- prerequisites;
- arming;
- evaluation mode;
- relation to location;
- direction;
- timeout;
- reset;
- invalidation;
- re-entry.

### Confirmation

Evidence that qualifies or agrees with a trigger.

Timing matters:

- pre-trigger filter;
- synchronous confirmation;
- delayed/post-trigger confirmation.

A post-trigger confirmation changes actual entry time and price; testing must not use the earlier trigger price.

### Confluence

Not ratified as its own universal role. It is better represented through graph composition:

- `AND`;
- N-of-M;
- score;
- multiple supporting bindings.

### Entry semantics

Distinct from the trigger:

- market/limit/stop;
- price basis;
- bar-close/intrabar;
- delay and order conditions.

### Invalidation

Distinct concepts may include:

- setup/thesis invalidation;
- arming-state invalidation;
- level invalidation;
- stop placement;
- open-position exit.

Their exact boundaries remained open.

## 6.5 Graph operators and relationships

The graph is unbounded, typed, Boolean, temporal, and stateful.

Proposed operators:

- `ALL` / `AND`;
- `ANY` / `OR`;
- `NOT`;
- `K_OF_N`;
- `SEQUENCE`;
- `WITHIN`;
- `UNTIL`;
- thresholds and scores.

Proposed typed relations:

- `at`;
- `after`;
- `only_if`;
- `arms`;
- `confirms`;
- `vetoes`;
- `invalidates`;
- `manages`;
- `exits`;
- depends-on/composed-with.

Expected state path:

```text
prerequisites
→ arming event
→ trigger event
→ synchronous or delayed confirmation
→ entry event
→ manage/exit
→ timeout, invalidation, reset, cooldown, or re-entry
```

Cardinality is unrestricted:

- multiple levels;
- compound triggers;
- multiple confirmations;
- alternative exits;
- nested branches;
- asymmetric long/short logic.

## 6.6 Concrete example

```text
Primitive:
  bullish-engulfing

Binding:
  use bullish-engulfing as an M5 trigger
  at the Asian-session high

Graph:
  Asian-session high
  AND liquidity sweep
  AND bullish engulfing
  AND London time window
  → enter
```

`[FG M941]`

---

# 7. Evidence, confidence, uncertainty, and provenance

## 7.1 Evidence layers

The intended pipeline preserves separate layers:

1. Raw/captured source or permitted immutable locator.
2. Source manifest and acquisition metadata.
3. Normalized transcript/text without interpretation.
4. Frames, clips, screenshots, OCR, cursor/drawing context.
5. Transcript-to-visual temporal alignment.
6. Atomic claims with exact locators.
7. Model/analyst interpretations.
8. Dictionary mappings, bindings, and strategy graph.
9. Later empirical findings kept separately linked.

Never flatten raw evidence, interpretation, standardization, and empirical status into one artifact.

## 7.2 Required evidence labels

Each operational statement should be marked as:

- source-stated/explicit;
- visually demonstrated;
- repeated-example inference;
- analyst/model inference;
- STRATS-added standardization/parameterization;
- unresolved.

Model output is interpretation, not ground truth.

Unknown thresholds, timing, order type, direction, exit logic, or unreadable chart values stay unknown.

## 7.3 Confidence dimensions

One aggregate confidence score was rejected.

Core recovered dimensions:

- extraction confidence;
- rule explicitness;
- source quality/completeness;
- ambiguity/unresolved status;
- empirical status;
- portability/market-transfer status.

More detailed proposed subdimensions included:

- source fidelity;
- locator precision;
- transcription/ASR quality;
- visual observability;
- interpretation/reviewer agreement;
- scope completeness;
- operational/codability completeness;
- promotional or cherry-picking risk.

Important distinctions:

- High extraction confidence does not mean the strategy has edge.
- Low extraction confidence does not mean the strategy is bad.
- A clear source claim can still be false or promotional.
- Empirical status must not rewrite the original source claim.
- Portability cannot be inferred from model confidence.

`[FG M831; GM M4065]`

## 7.4 Promotional and performance claims

Promotional content should be retained and labelled rather than silently removed.

Examples:

- win-rate claims;
- testimonials;
- course funnels;
- affiliate claims;
- cherry-picked outcomes;
- urgency language.

Such material can describe creator context, but cannot support an operational rule without separate evidence. Claimed performance remains unverified unless independently supported.

---

# 8. Source program

## 8.1 Source universe

Discussed sources included:

- YouTube videos, channels, and playlists;
- podcasts and long-form interviews;
- public social video;
- X posts and threads;
- Instagram/social posts;
- websites and articles;
- books and ebooks;
- academic and practitioner papers;
- PDFs;
- MQL5 articles and code;
- TradingView scripts;
- GitHub repositories;
- indicator and technical-analysis code;
- cTrader/AutoChartist-style tools;
- creator/channel archives;
- local saved media and documents;
- NotebookLM notebooks/corpora.

`Mind Math Money` was named as an example channel/source family, not the sole corpus. `[GM M4066]`

Quantpedia was only a possible later source and was not funded at the time.

## 8.2 Seed versus corpus

A supplied channel, playlist, topic, or notebook means:

- use it as a discovery seed;
- inventory it;
- classify it;
- expand to related sources;
- deduplicate;
- preserve creator/channel relationships;
- identify gaps.

It does not mean “process only this list.”

The user’s NotebookLM notebooks containing hundreds of sources should be treated as high-value source maps and corpora, not ignored.

## 8.3 One source can yield many outputs

A source must not be forced into one bucket. It may simultaneously contribute:

- one or more source-faithful strategies;
- a partial setup or entry hypothesis;
- reusable primitives;
- creator-specific definitions;
- mini-KB research;
- examples and counterexamples;
- risk or exit concepts;
- methodology context;
- performance or promotional claims.

Likewise, one long video may contain several strategies plus general education.

---

# 9. Video and long-source pipeline

## 9.1 Core rule

For chart-heavy trading videos, transcript-only extraction is insufficient.

The pipeline requires:

- transcript/audio evidence;
- visual/chart evidence;
- temporal reconciliation between the two.

`[FG M796, M831, M902; GM M4065]`

## 9.2 Full staged pipeline discussed

### Stage 1 — Inventory and acquire

- canonical URL/source ID;
- title, creator, channel, playlist;
- publication/retrieval metadata;
- access and rights state;
- hashes where permitted;
- media and caption availability;
- avoid duplicate acquisition.

### Stage 2 — Cheap deterministic transcript capture

- use native captions when available;
- preserve manual-versus-auto and language metadata;
- ASR/Whisper fallback;
- retain gaps and failure information;
- do not treat captions as perfect.

### Stage 3 — Normalize and chunk

- clean caption rolling duplicates and markup;
- preserve timestamps;
- split by chapters, topics, or timestamp windows;
- use overlap where needed;
- keep a coverage map and unprocessed ranges.

### Stage 4 — Transcript-first semantic triage

Locate candidate windows containing:

- strategy rules;
- “look here”/“this chart” deictic references;
- entry, stop, target, confirmation;
- timeframe/session/instrument;
- indicator settings;
- examples and counterexamples.

### Stage 5 — Targeted visual capture

For selected windows:

- extract pre/cue/post frames;
- preserve frame timestamps;
- use clips where state changes matter;
- inspect cursor/drawings/annotations;
- OCR text and chart values;
- record resolution and missing/illegible fields.

### Stage 6 — Multimodal interpretation

A vision-capable model examines:

- transcript;
- selected frames/clips;
- OCR;
- chart sequence;
- visible timeframe, instrument, indicator settings, and annotations.

### Stage 7 — Reconcile modalities

Explicitly record:

- transcript and chart agreement;
- transcript/chart conflicts;
- statements not visible;
- visuals not spoken;
- ASR uncertainties;
- analyst inference.

### Stage 8 — Atomize claims

Every operational assertion receives:

- exact time range;
- quote or literal visual observation;
- frame/clip reference;
- evidence class;
- confidence dimensions;
- ambiguity.

### Stage 9 — Normalize into STRATS

Map evidence to:

- dictionary entries/profiles;
- candidate-specific role bindings;
- logic graph;
- strategy package;
- lineage;
- mini-KB contributions.

### Stage 10 — Cross-source review

- reconcile terminology;
- detect duplicates and contradictions;
- use Gemini or NotebookLM for bounded ambiguity;
- preserve unresolved gaps.

## 9.3 Long-video policy

For multi-hour videos or podcasts:

- transcript-first;
- chunk by chapters or timestamp windows;
- identify relevant visual windows;
- avoid full-video high-density frame analysis by default;
- explicitly report uninspected ranges;
- download/cache once where permitted and reuse local media;
- do not imply complete coverage after examining a few clips.

The `claude-video/watch` tool was evaluated as a bounded evidence helper:

- one URL/local video per run;
- downloads or inspects metadata;
- retrieves captions or invokes Whisper;
- extracts timestamped JPEG frames;
- emits a Markdown evidence report;
- the hosting vision model, not `watch.py`, performs interpretation.

It was judged useful for selected short windows, not as the durable batch-ingestion backbone for three-to-five-hour material. `[GM M4065–M4066 supporting analysis; GM M4070 made long-video tooling later support]`

---

# 10. Deterministic scripts and cheap intake

## 10.1 Settled principle

Use cheap deterministic processing before expensive LLM analysis.

This reduces:

- repeated downloads;
- duplicated model work;
- context consumption;
- expensive visual passes on irrelevant material;
- loss of metadata/provenance.

## 10.2 Specific tools and functions discussed

### `yt-dlp`

- enumerate channels/playlists;
- canonical IDs and URLs;
- metadata/info JSON;
- chapters;
- subtitles/VTT/SRT;
- audio/video download;
- archive/deduplication support.

### `ffprobe`

- duration;
- stream presence;
- codecs;
- audio/video tracks;
- resolution and frame-rate metadata.

### `ffmpeg`

- audio extraction;
- clips and timestamp windows;
- uniform/scene/keyframe extraction;
- pre/cue/post frame sequences;
- media conversion.

### Transcript/subtitle scripts

- parse VTT/SRT;
- normalize timestamps;
- remove rolling-caption duplicates;
- preserve language/manual-auto status;
- split long transcripts;
- locate cue terms;
- track ASR gaps.

### Hashing/manifests/deduplication

- source IDs;
- content hashes where appropriate;
- retrieval metadata;
- canonical URL normalization;
- duplicate and already-processed checks.

### Documents

- MarkItDown for suitable office/PDF/document conversion;
- Firecrawl for public pages and difficult remote documents;
- OCR for scanned pages/images;
- ebook/PDF chapter/page and bibliography handling.

### Python/reference scripts

Useful for:

- deterministic parsers;
- technical-indicator reference semantics;
- alias/deduplication support;
- inventory/coverage reports.

These helper scripts are external construction tools. They do not turn STRATS into a codebase.

## 10.3 Status

The principle was endorsed. No final script suite, CLI, or required implementation was approved.

---

# 11. n8n usage

## 11.1 Intended role

n8n was discussed as a possible external batch-orchestration layer for stable, repeated workflows:

- source discovery and intake;
- persistent execution state;
- idempotency;
- retries and error routing;
- rate control;
- scheduling;
- queues;
- deduplication checks;
- dispatching transcript chunks or visual windows to Hermes workers;
- tracking coarse stages.

One concrete proposed stage sequence was:

```text
discovered
→ captioned / ASR-needed
→ transcript-ready
→ visual-candidates
→ visual-reviewed
→ normalized
→ QA
```

## 11.2 What n8n should not do

n8n should not:

- interpret trading concepts;
- perform chart reasoning;
- decide ontology;
- resolve source ambiguity;
- declare edge;
- become the canonical STRATS data model;
- parse human model prose as if it were a stable API;
- be required to read or maintain the library.

The intended division was:

```text
deterministic scripts/n8n:
  acquisition, metadata, state, queues, retries, dispatch

Hermes/vision/trading-domain agents:
  interpretation, visual analysis, normalization, graph/package work

STRATS:
  portable accepted plain-file knowledge
```

## 11.3 Status

n8n’s role was discussed, not ratified as required infrastructure.

It should be introduced only when a stable repetitive ingestion flow justifies it, not before the folder/dictionary design and not as the first solution for one source. It remains outside the STRATS folder architecture.

---

# 12. Gemini and NotebookLM

## 12.1 Gemini web app

Discussed roles:

- difficult chart/video interpretation;
- targeted visual escalation;
- resolving ambiguous source passages;
- comparing transcript and chart;
- “student-like” questioning to ask for explanations;
- second opinion where a worker is uncertain.

Preferences:

- the web application may be preferable to a paid API;
- the user can log in through the browser/preview himself;
- credentials must not be requested, stored, or reproduced;
- Gemini output remains model interpretation linked to evidence, not source truth.

It was not intended for:

- deterministic bulk metadata intake;
- canonical storage;
- replacing timestamps/frames;
- making unsupported trading claims.

## 12.2 NotebookLM

Discussed roles:

- query a large bounded corpus;
- compare hundreds of sources;
- identify repeated terminology;
- find contradictions;
- create creator/methodology/pair research summaries;
- support mini-KBs;
- ask source-grounded questions in a student-like way.

Important boundary:

- NotebookLM answers are synthesis, not raw evidence.
- Underlying citations/sources should be retained.
- For YouTube, NotebookLM is primarily useful for transcript-grounded analysis, not chart-pixel validation.
- Existing notebooks with hundreds of sources should be inventoried and treated as source maps.
- The local `nlm` CLI was found, but authentication/useful operations were not proven during Friendly Greeting.

---

# 13. Mini knowledge bases

## 13.1 Purpose

Mini-KBs provide durable contextual research that can be reused when:

- constructing a strategy;
- interpreting a source;
- enhancing a pair/session-specific idea;
- comparing methodologies;
- resolving terminology.

They belong inside STRATS’s knowledge area, not in QMX runtime state.

## 13.2 Domains discussed

- pairs;
- sessions;
- methodologies/families;
- macro drivers;
- styles/horizons;
- concepts/primitives;
- chart and candlestick patterns;
- indicators;
- liquidity and order flow;
- risk and exits;
- prop-firm constraints;
- creators and creator-specific terminology;
- potentially data/venue and execution-context topics.

## 13.3 Boundaries

Mini-KBs should contain:

- durable research;
- definitions;
- cited source claims;
- disagreements;
- examples;
- strategy and primitive links;
- historical fixed studies.

They should not contain:

- today’s mutable market bias;
- live spread/account/position state;
- current open trades;
- daily runtime intelligence;
- QMX agent memory;
- rolling operational snapshots.

## 13.4 Open classification issue

The relationship among these axes remained unresolved:

- methodology/family;
- macro domain/lens;
- style/horizon;
- execution archetype;
- individual strategy.

Specific corrections:

- SMC, ICT, and order flow can be broad methodologies or collections containing many strategies and concepts.
- Scalping is cross-cutting; it can use many methodologies.
- Macro may be its own knowledge domain or an analytical lens; it was not conclusively placed under methodologies.
- “Sniping” should not automatically become a complete methodology.
- `execution-archetype` was useful provisional language, not a frozen taxonomy.

`[FG M975; GM M4066, M4070]`

---

# 14. Lineage, variants, composites, and catalog

## 14.1 Lineage

Settled direction:

- A source-faithful baseline should not be silently overwritten.
- A changed trigger, filter, location, exit, or parameter should create a traceable child/variant.
- Variants should record semantic/component diffs rather than duplicate entire unrelated files.
- A composite/hybrid must name multiple parents.
- A generated composite must not be represented as if one source taught it.
- Source-defined and agent-generated variants must remain distinguishable.

Suggested lineage information:

- parents and children;
- `derived_from`;
- `variant_of`;
- `composed_of`;
- changed node/component;
- old value and new value;
- reason/hypothesis;
- inherited evidence;
- newly required evidence;
- source-native versus derived status.

The natural structure is a DAG, not a single linear tree.

`[FG M902, M941, M975; GM M4065–M4066]`

## 14.2 No single “magical best” variant

The discussions rejected collapsing all alternatives into one presumed winner.

Multiple valid alternatives may exist depending on:

- pair;
- session;
- horizon;
- data/feed;
- costs;
- downstream book/portfolio context;
- different trade-offs.

Empirical selection belongs downstream and does not erase lineage.

## 14.3 Catalog/index

The aspiration of roughly 7,000 strategies was an indication of desired scale, not a fixed verified acceptance count. `[GM M4066]`

At that scale, STRATS needs:

- stable IDs;
- global index/catalog;
- one-line human descriptions;
- source and creator links;
- package paths;
- methodology/style/horizon tags;
- pair/timeframe/session indexes;
- completeness status;
- parent/child/composite links;
- evidence/ambiguity status;
- aliases and deduplication;
- browse paths usable by humans and agents.

The user compared the desired index to a skills catalog: a concise global summary that lets an agent find the detailed folder only when needed.

Whether the catalog and lineage need dedicated physical folders or can largely use Markdown indexes/backlinks remained open.

---

# 15. Trading bots versus Hermes agents

The word “bot” was being used for two different things and needs explicit terminology.

## 15.1 Trading bots

These are market-facing algorithmic implementations of strategy logic.

They:

- consume a strategy candidate/specification;
- produce entry/exit behavior;
- are later implemented, tested, governed, or deployed through QMX or another platform.

STRATS stores knowledge and candidate definitions, not running trading bots.

## 15.2 Hermes bots/agents/subagents

These are research and construction workers.

They:

- read transcripts;
- investigate trading concepts;
- normalize sources;
- inspect visuals;
- build candidate dictionary entries;
- compare sources;
- draft packages and mini-KBs.

They do not trade merely because they are called bots.

## 15.3 Recommended terminology

To avoid future confusion:

- use **strategy candidate/package** or **candidate trading-bot definition** for the market logic artifact;
- use **research worker**, **Hermes agent**, or **subagent** for construction agents.

The research workers are not part of the STRATS runtime architecture.

`[FG M831, M902; GM M4066]`

---

# 16. Model assignments and exclusions

## 16.1 General preference

The user wanted:

- the right model for each task;
- provider/model diversity to reduce correlated errors;
- efficient use of quotas;
- preservation of the main session’s context by delegating bounded work;
- no defaulting every worker to GPT‑5.6 Sol;
- no elaborate route-probing campaign for its own sake.

## 16.2 Task assignments discussed

### Main/high-end orchestrator

Best suited for:

- synthesizing the recovered decisions;
- resolving architecture/taxonomy;
- reviewing folder layout;
- reconciling conflicting worker outputs;
- communicating the few real decisions to Mubarak.

### DeepSeek V4 Flash/Pro

Preferred as:

- fast text-only workhorse;
- transcript extraction;
- classification;
- deduplication;
- high-volume source and ontology research.

Operational rule: do not assign chart/video/visual work to DeepSeek.

### GPT-5.6 Terra/Luna/Sol and other vision-capable GPT routes

Discussed for:

- architecture and synthesis;
- chart-heavy sources;
- visual review;
- difficult structured extraction;
- coding or deterministic helper tasks where relevant.

Terra and Luna via Codex were explicitly requested as efficient alternatives to using Sol for every worker.

### Gemini web

- manual/high-value visual escalation;
- ambiguous charts and clips;
- student-like source questioning.

### NotebookLM

- cross-source synthesis and citation-grounded comparison;
- not visual chart analysis.

### Qwen/GLM and other models

Potential independent workhorses where capability and route availability are appropriate. No fixed permanent assignment was settled.

## 16.3 Exclusions

Settled preferences:

- no Grok;
- no Kimi K3;
- DeepSeek is text-only for routing purposes.

Other Kimi models were not universally banned, though they required a working route.

## 16.4 OpenCode clarification

A post-compaction assistant incorrectly generalized the user’s dislike of needless external coding wrappers into a blanket “no `opencode-go` provider” rule.

That should not be memorialized as settled:

- external coding-agent layers/wrappers were considered unnecessary for simple work;
- `opencode-go` itself had previously been used intentionally as a Hermes provider route;
- the real settled preference is task-appropriate direct Hermes routing with minimal unnecessary layers.

---

# 17. Pre-regression population methodology

This is distinct from the later four-worker dictionary launch.

## 17.1 User-directed orchestration sequence

The user explicitly asked for:

```text
extract/recover the session transcript
→ give it to specialist bots
→ have them break it down
→ produce the actual plan
→ independently validate the plan
→ build the folder/library structure
→ begin real ingestion and population
```

`[FG M983, transcript around the user message following the first draft plan]`

The reason was to preserve the main agent’s depleted context, not to create a permanent governance bureaucracy.

## 17.2 Earlier safe specialist sequence

The pre-regression design proposed:

1. Give each worker an immutable transcript/source packet.
2. Require structured findings with citations and unresolved questions.
3. Run an adversarial cross-review.
4. Merge a draft architecture.
5. Show the draft to Mubarak.
6. Only after approval, create canonical files.

Proposed roles included:

1. Session archaeologist.
2. Trading ontology researcher.
3. Strategy-graph architect.
4. Evidence/provenance architect.
5. QMX-boundary analyst.
6. Video-pipeline specialist.
7. Books/document specialist.
8. Tool/source scout.
9. Adversarial reviewer.
10. Synthesis agent.

The later “leave QMX out” decision makes a dedicated QMX-boundary worker unnecessary for the current layout.

## 17.3 Population flow after a usable layout

The intended substantive population flow was:

1. Inventory already-owned/local/subscription sources.
2. Treat playlists/channels/topics/notebooks as seeds.
3. Expand discovery and deduplicate.
4. Run cheap deterministic capture before LLM analysis.
5. Preserve raw evidence and normalize transcript/text.
6. Extract atomic claims.
7. Align chart-heavy transcript and visuals.
8. Map to dictionary concepts and source-specific profiles.
9. Create role bindings and strategy graphs.
10. Build strategy packages and mini-KB contributions.
11. Record lineage and catalog entries.
12. Reconcile cross-source aliases, contradictions, and gaps.
13. Continue in production waves until the library is materially populated.

## 17.4 Pilot versus product

There was an evolution:

- Friendly Greeting agents recommended one real chart-heavy vertical slice before locking large schemas.
- Mubarak later stressed that a pilot is not the deliverable and that STRATS must be substantially populated.
- Gold Mine then corrected another sequencing error: eventual population is required, but the immediate next action should be an approved plain-folder layout, not an overengineered population campaign.

Correct combined interpretation:

- a pilot may expose structural problems;
- it must not become a fake project-completion milestone;
- the eventual deliverable is substantial population;
- the physical layout should be approved before large-scale population.

---

# 18. Post-compaction worker launch and freeze

Everything after `GM M4071` is a post-compaction execution branch, not proof that the pre-compaction design had been completed.

## 18.1 What happened

The assistant:

- probed model routes;
- wrote a shared dictionary contract;
- created four worker prompts;
- targeted approximately 185–250 candidate primitives; `[GM M4122]`
- launched four background workers. `[GM M4150–M4153]`

The worker areas were:

- locations/market structure;
- triggers/patterns/transitions;
- context/filters/confirmations;
- exits/execution/management.

## 18.2 State at the freeze

At the recorded stopping point:

- DeepSeek V4 Pro had produced 66 context/filter candidates.
- GPT‑5.6 Terra had produced 57 exit/execution candidates.
- DeepSeek V4 Flash and GLM had exited with no artifact.
- Seven orchestration-scratch files existed:
  - one shared contract;
  - four prompts;
  - two candidate artifacts.
- No canonical STRATS content had changed.

The final freeze prohibited:

- worker restarts;
- replacements;
- consolidation;
- deduplication;
- curator/reviewer chains;
- promotion into STRATS;
- further dictionary work.

`[GM M4150–M4193]`

## 18.3 Why it was stopped

It recreated the previously rejected pattern:

```text
model probing
→ specialist fleet
→ staging
→ curator/reconciliation
→ promotion gates
```

That was orchestration overgrowth, not the simple transcript → plan → approve → build/populate methodology the user wanted.

The scratch outputs were not an accepted dictionary and did not settle the folder layout.

---

# 19. Settled, provisional, and rejected decision ledger

## Settled

- STRATS is a portable plain-file/Obsidian knowledge library.
- It is not a software system or QMX subsystem.
- Bots/tools may construct it but are not runtime dependencies.
- Primitive identity, contextual role binding, and strategy logic are separate layers.
- Four pillars are useful human-facing lenses, not closed ontology classes.
- A strategy may have any number of components.
- The dictionary must be large, extensible, reusable, and evidence-backed.
- Short dictionary lists are examples only.
- Strategy-specific scope, timing, role, and parameters belong in bindings.
- Graphs require Boolean, temporal, state, and execution semantics.
- Unknowns and missing exits must remain visible and must not be invented.
- Source-native risk/exit material should be preserved.
- Evidence/provenance and multimodal alignment are first-class.
- One aggregate confidence score is misleading.
- Strategy packages, lineage, variants, and composites are directionally accepted.
- Mini-KBs belong in STRATS as durable research.
- Live intelligence/runtime state does not.
- QMX adapters, execution/results machinery, and runtime governance are out of current STRATS.
- Chart-heavy videos require transcript plus visual analysis.
- Cheap deterministic intake should precede expensive model work.
- Gemini and NotebookLM are supporting tools, not authorities.
- Model routing must respect modality.
- No Grok, no Kimi K3, no DeepSeek visual assignments.
- Long-video tooling is supporting work, not the immediate foundation.
- Eventual substantial population is required.
- Mubarak is a developer, not the trading-domain authority; agents must normalize terminology and do the domain research.

## Provisional/open

- Final folder tree.
- `dictionary/` versus `primitives/`.
- Global binding templates versus package-local bindings.
- Exact strategy package files.
- Markdown/YAML/front-matter balance.
- Exact dictionary schema.
- Exact graph keywords/serialization.
- Macro placement.
- Methodology/family taxonomy.
- Style/horizon representation.
- `execution-archetype` terminology.
- Whether incomplete strategies receive folders, tags, or a looser status.
- Exact mini-KB taxonomy.
- Source physical hierarchy versus indexes/tags.
- Catalog versus lineage folder responsibilities.
- Whether n8n is eventually warranted and its exact deployment.
- Gemini/NotebookLM operational workflow and authentication.
- First pilot/source selection after layout approval.
- Exact population coverage targets.
- The 7,000-strategy figure as aspiration versus measurable target.

## Rejected or superseded

- Rigid four-column/four-pillar schema.
- Treating roles as permanent primitive classes.
- Inventing thresholds, stops, exits, or risk defaults.
- One scalar confidence score.
- One “magical best” variant replacing all alternatives.
- Unrelated copied strategy files with no lineage.
- STRATS as a “human-reviewable operating system.”
- QMX adapters as a current requirement.
- Executable test manifests, results, ledgers, optimizers, and certification inside STRATS.
- Package locks and software-release machinery.
- Live intelligence snapshots inside STRATS.
- Runtime databases/account state/agent memory.
- Route-probing and curator/promotion ceremony as the core population methodology.
- Treating `entry_hypothesis` as a compulsory classification for every incomplete source.
- Treating scalping as one methodology.
- Treating “sniping” as automatically a complete methodology.
- Treating the old QMX documentation as the current implementation.
- Blanket prohibition on the Hermes `opencode-go` provider.

---

# 20. Best concise handoff for the next session

The next session should begin from these facts:

1. STRATS is a portable Obsidian/plain-file trading knowledge library.
2. Its semantic core is settled:
   `primitive dictionary → contextual binding → strategy logic graph`.
3. Evidence, uncertainty, strategy packages, lineage, catalog, and mini-KBs are required.
4. QMX, runtime testing, adapters, results, and live intelligence stay out.
5. The exact folder tree is not settled despite several strong candidates.
6. The first design task is to present a corrected empty-folder tree plus one complete example strategy-folder interior for Mubarak’s approval.
7. That tree must include the full source universe, a role-neutral dictionary, strategy classes without forcing `entry_hypothesis`, mini-KBs including macro and creator terminology, and non-duplicative catalog/lineage.
8. Only after approval should empty folders be created and population resume.
9. Existing post-compaction dictionary artifacts are scratch, not canonical authority.
10. Population must eventually be substantial; pilots and schemas are not the final product.

No files were modified and no agents were launched during this recovery. Credentials appeared in historical session material, but all sensitive values remain `[REDACTED]`.