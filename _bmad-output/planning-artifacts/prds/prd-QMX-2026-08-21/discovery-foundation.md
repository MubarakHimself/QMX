# PRD Discovery Extract — QMX Foundation

**Role:** PRD discovery extractor. This document captures PRD-relevant content ONLY —
product purpose, operators, capability groups (candidate functional-requirement families),
NFR signals, constraints/invariants, explicit exclusions/deferrals, and open gaps. It
records capabilities, never implementation detail. Each claim cites its source file.

**Corpus status (all sources):** every doc is `status: provisional`. Nothing here
authorizes implementation, live money, credential use, or destructive action. Answered
gaps are operator rulings, not build/live authority. (index.md, AGENTS.md, constitution.md L29)

---

## 1. Product purpose — what QMX / QMF is

- **QMX** is "the operator's broader algorithmic and quantitative trading platform. QMX
  applications consume QMF libraries and modules." (glossary.md — QMX)
- **QMF** = "the reusable Quant Mind Framework toolbox from which QMX applications are
  built. QMF is not an application or runtime." (glossary.md — QMF)
- QMF V1 is "a contracts-first Python toolbox consumed by QMX applications." It provides
  **five reusable libraries and two modules**; it explicitly does NOT provide an
  application loop, scheduler, product UI, backtesting library, or trading-node runtime.
  (architecture/overview.md)
- The documentation target is the **QMF V1 Blueprint** (qmf-core, qmf-registry, qmf-data,
  qmf-indicators, qmf-structure, Venue module, Risk module). (constitution.md L12; glossary.md)
- Design paradigm: "contract-hub library workspace, hexagonal at workspace scale." `qmf-core`
  is the dependency-free hub of definitions; every other package depends inward on it;
  runtime concerns enter through protocols. (architecture/overview.md)
- Everything downstream of QMF — trading node, backtesting, agentic system, product UI —
  is built WITH QMF libraries and must not re-implement or bypass its contracts.
  (constitution.md L31; AGENTS.md)
- Asset scope: Forex is only the first seeded consumer; qmf-core must not assume Forex,
  cTrader, scalping, or a deployment environment. Permanent exclusion: **no futures, no
  options**; stocks may come later. (constitution.md L16; gap-report.md DEC-0015)

---

## 2. Who operates it — actors / users

- **Operator** — the single human principal. Operates QMX applications; runs experiments
  via the qmb CLI; is the sole promotion authority; signs admissions; makes/overturns
  rulings. Non-technical (per project memory, not in docs). (overview.md C4 context;
  constitution.md L17)
- **Operator's agent** — an agentic actor that may author bots and run experiments
  alongside the operator ("operator- or operator's-agent-authored"). (glossary.md —
  conformance; overview.md QML/QMB diagrams)
- **Coding agents** — QMF code and docs must be legible to human developers and coding
  agents; AGENTS.md is their entry point. (constitution.md L5; AGENTS.md)
- **Authority hierarchy (L36):** `bot -> book -> BMS -> operator`. Bots trade; books
  control bots; BMS accounts for and constrains books; nothing above a bot touches the
  market. QMF may never invert or shortcut this. (constitution.md L36)
- External systems (peers, not users): cTrader Open API (venue), Dukascopy (historical
  data), news-calendar feed, off-machine object storage. (overview.md; dependencies.yaml)

---

## 3. Subsystem map (candidate capability domains)

### QMF roster — five libraries + two modules (the V1 deliverable)
(constitution.md L14; stack.md roster table; dependencies.yaml)

1. **qmf-core** (backend library) — definitions-only, asset-neutral foundation: exact
   money/time primitives, domain nouns, typed refusals, the single `fp1` fingerprint
   serializer, protocol seams. Zero outside dependencies. Owns no broker, event loop,
   backtest, download, or node runtime. (components list; constitution.md L13; glossary.md)
2. **qmf-registry** (backend library) — identity, per-kind records, fingerprint-derived
   ids, append-only typed lineage edges, causality-gate, attempt, promotion skeleton.
   Owns every registry kind incl. Bot (CT-33) and confluence (CT-34). (index.md; dependencies.yaml)
3. **qmf-data** (backend library) — governed bitemporal evidence, seven room-roles,
   datasets/splits/holdout seal, journal, source adapters, backup primitives. (index.md)
4. **qmf-indicators** (backend library) — package-neutral two-mode (batch+streaming)
   indicator protocol (CT-16), series vocabulary, TA-Lib wrapper. (index.md)
5. **qmf-structure** (backend library) — QMX-owned causal market-structure objects
   (levels, zones) under CT-17 lifecycle. (index.md)
6. **qmf-venue** (middleware module, edge — nothing imports it) — venue-neutral adapter
   seam: secret lifecycle, four-command uncertainty law, one-port four-contract adapter;
   cTrader first target. (index.md; overview.md)
7. **qmf-risk** (backend module, edge — nothing imports it) — Book/BMS binding chain,
   exit ownership, paper mode, control actions, protection windows, SQS, R/dimensional
   law, bench/performance evidence. (index.md; overview.md)

**Internal seams of qmf-data (not public packages):** qmf-data-ingest (middleware),
qmf-data-store (data), qmf-data-backup (data). (overview.md C4 L2)

**Calendar extensions (outside roster, own SemVer):** qmf-calendar-forex is the first
market-hours calendar extension implementing CT-02. (index.md; dependencies.yaml)

### Application-layer consumers — built ON QMF, outside the roster and outside QMF V1

- **QMB** — the QMX experimentation/backtesting product: one pure library + the `qmb`
  CLI in one wheel. Composes the six backend QMF libraries in `world = replay`; produces
  CT-32 results and CT-13 journal streams; takes NO venue edge. First sanctioned place
  the defined-unwired risk contracts are legally wired. Realizes the reserved "future
  backtesting library" slot. A library and CLI, never an "engine" or "kernel." (overview.md;
  glossary.md — QMB; dependencies.yaml COMP-QMB)
- **QML** — the QMX bot-authoring library: one uv-installable pure library (`import qml`).
  Authors the two Bot-domain registry kinds (CT-33 Bot definition, CT-34 confluence),
  defines the bot runtime protocol, owns the conformance gate. Imports qmf-core,
  qmf-registry, qmf-risk; never qmf-venue. A governed bot = exactly two artifacts (CT-33
  declaration + plain-Python logic); the `.qml` DSL is NOT revived in V1. (overview.md;
  glossary.md — QML; dependencies.yaml COMP-QML)

### External peer systems (external layer, no live connection authorized)
- **COMP-CTRADER** — cTrader Open API, first intended venue peer. (dependencies.yaml)
- **COMP-DUKASCOPY** — historical tick source. (dependencies.yaml)
- **COMP-CALENDAR-FEED** — news/economic-calendar feed. (dependencies.yaml)
- **COMP-OBJECT-STORAGE** — off-machine backup destination. (dependencies.yaml)

### Deferred / future consumers (outside V1)
- **Simulator** — deferred product UI, will consume QMB. (glossary.md — Simulator)
- **Trading Node** — later QMX application owning live-trading runtime & orchestration.
  Outside QMF V1 docs. (glossary.md — Trading Node)
- **MIS** — future trading-node analytical/ML ensemble. Not a V1 library. (glossary.md — MIS)
- **Agentic runtime** — deferred outside QMF V1. (gap-report.md DEC-0091)

---

## 4. Capability groups (candidate functional-requirement families)

Grouped by domain; each is a capability the platform must eventually offer. Source: the
per-component index entries, contract list, and glossary. Implementation detail omitted.

**A. Value & identity foundation (qmf-core)**
- Exact money/price/quantity as scaled integers; binary float banned on the money path
  (taint rule). (constitution.md L24; glossary.md — Money path; gap-report GAP-0007)
- Exact time: int64 UTC nanoseconds, CivilDate vs TradingDate, wall vs monotonic clocks,
  injected Clock protocol. (gap-report GAP-0008)
- Deterministic content-addressed identity (`fp1` fingerprint). (gap-report GAP-0010)
- Typed refusals — seven categories shared across every public boundary. (gap-report GAP-0011)
- Result label with worlds (live/replay/simulated). (gap-report GAP-0012)

**B. Registry, identity, lineage, promotion (qmf-registry)**
- Per-kind versioned records; fingerprint-derived stable ids; addable-never-redefined kinds.
- Append-only typed lineage edges (supersedes, promoted-from, occurrence-of, corroborates,
  disagrees-with).
- Human-only promotion into the live zone (promotion-occurrence card). (gap-report
  GAP-0014/0015/0019; constitution.md L17)
- Bot kind (CT-33) and confluence kind (CT-34), strategy-family metadata record.

**C. Governed data & evidence (qmf-data)**
- Seven room-roles instantiated per world; cross-world read refused.
- Bitemporal evidence (event-time + knowledge-time), idempotent intake keyed on
  (source, source-native id, revision).
- Dataset splits (train/validation/untouched-test) + 12-month sealed holdout no-peek lock.
- Journal: seven event types in append-only per-writer streams.
- Backup primitives: nightly, encrypted, versioned, off-machine (schedule owned by apps).
  (constitution.md L18/L19; gap-report GAP-0020..0030)

**D. Indicators & market structure (qmf-indicators, qmf-structure)**
- Two-mode (batch + streaming) indicator protocol with an equality law; TA-Lib canonical
  arithmetic; light/heavy placement rule. (gap-report GAP-0031..0033)
- Causal structure objects (families of chart objects) minted once, evolved by append-only
  interaction records; evidence-class identity-bearing. (gap-report GAP-0034)

**E. Venue integration (qmf-venue)**
- Venue-neutral one-port, four-contract adapter (capability / command / event / secret-session).
- Five command kinds: place_order, cancel_order, close_position, close_all, amend_protection.
- Four-outcome uncertainty law (accepted / rejected / denied-locally / UNKNOWN); UNKNOWN
  blocks its command stream until explicit resolve_unknown.
- Secret lifecycle: references not values; connection manager holds values only.
- Market data (ticks/bars/depth/backfill) enters as CT-10 via qmf-data intake.
  (gap-report GAP-0035..0038; overview.md)

**F. Risk / Book / money management (qmf-risk)**
- Book/BMS binding chain (BMS account-facing, one per account serving many Books; Book
  binds one BMS; Bot binds one Book).
- Template-and-versioning discipline (git-logic versioning; per-variable ui-editable flags).
- Three-layer admission (linters, demo/paper shakedown, one operator signature; no probation).
- Book-owned exit policy; Bot proposes risk-monotonic exits through the CT-23 door.
- Paper mode as a Book-level standing evidence state.
- Control actions: kill switch (global) vs kill line (per-Book capital floor); same-tick
  priority arbitration; exit-preservation invariant.
- Protection windows (news, daily_dead_zone, session_handover_buffer).
- SQS (Spread Quality Sensor) block-only producer.
- R / numeraire (USD) / dimensional unit-kind law.
- Exit records, bench fold, performance-result container (CT-32).
  (gap-report GAP-0039..0046; overview.md)

**G. Experimentation / backtesting (QMB — application layer)**
- Config compiler ("wind tunnel"), pure `run()` returning CT-32, impure orchestrator
  owning writes; reader-derived per-requirement verdicts; fill/slippage/cost/financing
  fidelity seams under an optimistic taint; registry as-of sets over a passive file-sync hub.
  (index.md — QMB; overview.md)

**H. Bot authoring (QML — application layer)**
- Author-side types/helpers producing CT-33/CT-34; bot runtime protocol; two-layer
  conformance gate + four-check prediction linter; strategy-family keying; footprint
  manifest; advisory stop proposal with Book-side full-loss derivation; exit reconciliation.
  (index.md — QML; overview.md)

---

## 5. NFR signals

- **Legibility:** QMF code + docs must be legible to human developers AND coding agents.
  (constitution.md L5)
- **Determinism / reproducibility:** fingerprints deterministic across platforms; floats
  refused in identity content; identical work from two sandboxes deduplicates. (glossary.md —
  Fingerprint, Computation identity)
- **Performance (measure-then-budget):** no invented numbers; every component ships a
  benchmark harness measuring speed + peak memory at load ladders; first measurements
  become fingerprinted (OS, CPU-class) baselines that gate tier-2 merges. Reference
  scenario ~40 bots (10/100/200 marks). Only stated design constraint: `qmf-core` imports
  in well under one second. (stack.md Performance budgets; gap-report GAP-0013)
- **Quality gates:** ruff (format+lint), pyright strict, pytest; coverage floor 80%, 100%
  branch coverage on CT-01/CT-02 primitive modules; three-tier pipeline (poe check /
  check-integration / check-release). (stack.md; gap-report GAP-0003/0004)
- **Concurrency:** immutable values; one-writer-per-stream with unlimited readers; QMF
  never spawns threads/background work — the application owns all concurrency; async only
  at the venue network edge. (overview.md Concurrency stance; gap-report DEC-0113)
- **Observability:** loud/traceable failure; journal is evidence, not a log bus; seven
  journal event types. (AGENTS.md; gap-report GAP-0025)
- **Durability / recovery:** complete raw evidence kept forever + off-machine backup;
  migrations preflight→backup→dry-run→migrate→verify, never in-place mutation of the only
  copy; numeric RPO/RTO deferred to node/ops sitting. (constitution.md L18; stack.md;
  gap-report GAP-0022/0027)
- **Security:** secret references never values; secrets never in repos, config, journals,
  evidence, fingerprints, or logs; tier-1 secret-scan gate on `poe check`. (constitution.md
  L34; glossary.md — SecretValue)
- **Runtime targets:** CPython 3.14 pinned; tier-1 OSes Windows 11 x86-64 + Ubuntu LTS
  x86-64; pure-Python, OS-neutral. (stack.md Runtime matrix; gap-report GAP-0001)
- **Versioning discipline:** two ladders — SemVer lockstep code packages (one-release
  deprecation) + per-contract integer format versions whose meaning never mutates; history
  append-only, old evidence always readable. (stack.md; gap-report GAP-0005; constitution.md L15/L28)
- **No model training** in V1. (stack.md Model training)

---

## 6. Constraints / invariants that shape requirements

The 39 constitutional laws are the hard invariants. Highest-leverage for a PRD:

- **L1–L3** Operator rulings govern; GitBook + node docs are risk/sizing authority;
  research is evidence until adopted.
- **L4** Documentation and review precede implementation; deep design one topic at a time.
- **L7–L8** QMF is a toolbox, not an application; loops/orchestration/scheduling/UI stay outside.
- **L13/L16** qmf-core is definitions-only, asset-neutral (no broker/loop/backtest/download/node).
- **L14** Roster is exactly five libraries + two modules.
- **L15/L28** Contracts versioned from birth; evolve by durable versioned extension, not
  foundational replacement.
- **L17** Only a human may promote into the live zone.
- **L18–L20** Preserve raw evidence + off-machine backup; expose research via explicit
  splits; synthetic data never validates trading edge.
- **L21–L22** First venue = cTrader Open API from Python (never MQL), behind a venue-neutral seam.
- **L24** R = original pre-trade risk unit (never realized profit/equity/return).
- **L29** Provisional contracts/GAPs grant no implementation or live-money authority.
- **L30** Default-deny dependency direction (roster-scoped): qmf-core depends on nothing;
  every package may depend on qmf-core; only ratified inter-library edge is
  qmf-registry→qmf-data; nothing imports qmf-venue/qmf-risk. Applications on the workspace
  (QMB, QML) may consume qmf-risk at their own composition root but never import qmf-venue.
- **L31** Everything downstream built with QMF libraries; never bypass its contracts.
- **L32** No rule/vocabulary may name or privilege any trading school (school-neutral terms only).
- **L33** Plain-Python authoring always legal; enters governed evidence only via the
  extension/graduation path with a lineage edge.
- **L34** Components handle secret references, never values.
- **L35** Four-outcome venue law; a timeout is never a rejection; UNKNOWN blocks its stream.
- **L36** Authority order bot → book → BMS → operator; never inverted.
- **L37** GitBook + trading-node docs authoritative for risk/sizing/live-trading;
  QMX-discussion layer barred there.
- **L38** Configurable = UI-editable at platform level; recorded numbers are evidence,
  never ratified constants.
- **L39** Exit-preservation invariant: no control action may block a risk-reducing act or
  evidence recording; the blocking half of any control is entries only.
  (all: constitution.md)

Other structural invariants:
- Worlds & storage separation: non-live world may never write the live evidence namespace;
  storage separation (not identity distinctness) delivers world separation; data rooms per
  world. `world = simulated` is reserved-unusable in V1 (policy rejection). (overview.md;
  glossary.md — World)
- Read-time folds: runtime state (Book mode, seat state, order state, bench counts,
  standing intent, structure lifecycle) is a read-time fold over append-only streams, never
  a stored mutable field. (glossary.md — Read-time fold, fold contract)
- Node-material boundary (DEC-0142): trading-node runtime material (order path, protection
  funnel, startup, flatten-authority) stays out of QMF docs, pointer only. (AGENTS.md)

---

## 7. Explicit exclusions & deferred scope

**Permanent exclusions:**
- No futures, no options (stocks maybe later). (gap-report DEC-0015)
- No third-party strategy-family libraries; no foreign-platform contract transplant
  (Nautilus/CCXT contracts rejected as foundation). (gap-report DEC-0014/0085/0086)
- No database server; no centralized always-on backtesting service. (gap-report DEC-0084;
  overview.md)
- QMF trains/fine-tunes no model in V1. (stack.md)

**Deferred outside QMF V1 (separate future sittings/products):**
- Trading node live runtime & orchestration. (glossary.md; DEC-0142)
- Simulator product UI (will consume QMB). (glossary.md — Simulator)
- MIS analytical/ML ensemble. (gap-report DEC-0089)
- Agentic runtime organs (context, disposers, event buses, harness). (gap-report DEC-0091)
- Prop-firm Books / funded-account workflows (day-boundary calendar holds the seam only).
  (gap-report DEC-0081/0082)
- Product UI generally (QMF has no UI layer). (stack.md; overview.md)

**Retired / banned vocabulary** (never revive): "kernel", "exam"/"Broker Exam",
"engine" (for backtesting), "plugins" (say extensions), "snapshot" (say as-of set),
"timeframe" (say BarSpec), "stop-out", "BotSpec" (say Bot definition), "archetype"
(say strategy family), "minimal core", DPR, PRS, FORM-0006, Program/Campaign,
Snapshot Quality Sensor. (AGENTS.md; gap-report Dead decisions; glossary.md Retired names)

---

## 8. Open gaps flagged in the gap report

**State summary:** 49 gaps total — **45 answered**, **2 deferred to the backtesting
sitting**, **2 deferred consumer gaps**. No blocking gap remains open (Open gaps — 0).
(gap-report.md)

- **GAP-0016** (deferred) — the exact look-ahead / causality **registration gate** test
  and its pass evidence. QMB delivered look-ahead *prevention* by construction, but the
  registration gate itself stays deferred. Consequence: artifacts registered before the
  backtesting sitting carry no causality evidence (not retroactively reconstructible).
- **GAP-0017** (deferred) — the **attempt counter** (what it counts, scope, reset, budget
  effect). Raw material accrues by construction; the counting policy is deferred.
- **GAP-0048** (deferred, *partially closed*) — future backtesting-library **fidelity
  content**: fidelity-taxonomy values, calibration content, parity contracts, and
  simulated-time typing (which would unlock `world = simulated`). Seams already ruled;
  taxonomy/calibration still owed to its own sitting.
- **GAP-0049** (deferred) — the preregistered **search-quality threshold** (SR* definition,
  units, evaluation population, attempt-budget effect). Deferred to the research-threshold sitting.
- **GAP-0047** (QML bot authoring) — now **ANSWERED** by the 2026-08-21 QML increment.

**One open ledger decision (non-gap):** DEC-0049 — whether automatic data/quality
detectors may mutate trading state (they may notify; mutation not adopted). (gap-report Open ledger decisions)

**Zero live conflicts.** The last conflict (DEC-0067 exit ownership) was resolved by
DEC-0147. (gap-report Conflicts — 0)

**Resolved operator flag:** Dukascopy data-licensing ruled closed — personal-use
backtesting only, no redistribution. (gap-report; changelog.md)

---

## 9. Authority / source rules (for the PRD writer)

- Operator's current direct rulings win when sources disagree (L1).
- GitBook supplies Book/BMS governance baselines; for risk/position-sizing/live-trading,
  GitBook + trading-node docs are authoritative and the QMX-discussion layer is barred (L2, L37).
- Research/study deliverables are evidence only until an operator ruling adopts them (L3).
- Answered gaps are operator rulings but do NOT lift the corpus-wide provisional gate; the
  operator must re-ratify the whole knowledge base before provisional statuses are removed.
  (AGENTS.md Current release gate; gap-report Ratification handoff)
- BMad path from here (project CLAUDE.md + memory): corpus sign-off → PRD → epics/stories →
  factory coding. PRD and Architecture are the only required BMad steps; Architecture has
  already run (spine ratified). (project rules; changelog.md "Remaining BMad path")
