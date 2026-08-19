# QMF V1 ratification packet

**Status:** provisional Stage 4 review packet — **not a signature and not a ratification record**.

This packet makes the unresolved decision surface reviewable. A recommendation is a proposed path for the operator to accept, reject, or amend; its presence here never converts a conflict, gap, study, or provisional ledger entry into an answer.

## 1. Conflicts requiring an operator ruling

| Conflict | Competing readings | Recommended path — not an answer | Reason for the recommendation |
|---|---|---|---|
| **DEC-0040 / GAP-0018 — Bot-to-confluence cardinality** | Earlier evidence describes one confluence plus a Book binding; the later direct correction permits multiple confluences. | Ratify **one-or-more confluences per Bot**, with one explicit Book-binding reference. | The multiple-confluence statement is the later direct correction, but the schema must remain open until the operator explicitly resolves the conflict. [`EXT-0161`, `EXT-1126`] |
| **DEC-0067 / GAP-0040 — exit ownership** | One reading leaves ordinary exits with Bots and forced exits with Books; repeated corrections place Exit, including dynamic SL/TP and fast invalidation, in Book/risk territory. | Ratify **Book ownership of exit policy**, with Bots allowed to emit exit signals through a Book contract. | The direct corrections repeatedly place Exit in Book territory, while the GitBook baseline retains Bot exit organs; implementation would diverge unless the split is ruled explicitly. [`EXT-0020`, `EXT-0067`, `EXT-0136`, `EXT-0253`, `EXT-1125`] |

**Operator prompt for each conflict:** Ratify the recommended reading, or state the ruling you want.

### Evidence caveat that must survive ratification

Part of the operator's long answer in `SRC-01-C0022` is absent from the transcript export. The assistant's immediate recap preserves recorded rulings about Book-level paper mode, no parallel Bot paper twin / one Bot to one Book, full raw retention, and related demo-account handling, but the direct words are unavailable. **Recommendation:** ask the operator to confirm that those restatements stand exactly as recorded. **Reason:** this preserves the rulings without fabricating a direct quote or overstating their evidence class. [`EXT-0213`–`EXT-0216`, `EXT-0232`]

## 2. Blocking gaps

All 45 items below remain open and blocking. The “recommended path” column is preparation for the decision conversation, not an adopted contract. **Operator prompt for every GAP row:** Ratify the recommended path, or name the answer you want.

### Foundation, contracts, and quality gates

| Gap and question | Recommended path — not an answer | Reason |
|---|---|---|
| **GAP-0001** — Which CPython minor, operating systems, and CPU architectures are supported? | Pin one CPython minor for V1 and explicitly support the operator's Windows workstation plus the Linux VPS target. | Reproducible packages and CI matrices require a bounded runtime; the transcript names the environments but no exact version. |
| **GAP-0002** — What repository layout, namespaces, build backend, dependency manager, and lockfile policy apply? | Use a monorepo/workspace, one package per component, `pyproject.toml`, and a reproducible lock. | The final component roster is settled directionally, but no build/package convention is source-ratified. |
| **GAP-0003** — Which formatter, linter, type checker, test runner, coverage policy, and local commands are mandatory? | Select one fast formatter/linter, a strict type checker, `pytest`, and stable documented commands. | Factory agents need one deterministic quality path; the transcript does not select tools or thresholds. |
| **GAP-0004** — What runs at PR, merge, and release CI tiers? | PR: format/lint/types/unit; merge: integration/contract; release: build/install/migration/smoke. | The stages have different feedback-cost tradeoffs, and no tiering is currently defined. |
| **GAP-0005** — What release, SemVer, deprecation, and compatibility policy governs packages and schemas? | Version packages and schemas explicitly; forbid silent semantic mutation; require a deprecation window and migration note. | “Versioning from birth” is law, but its release mechanics are absent. |
| **GAP-0006** — Which dependencies and licences are allowed? | Ratify a small compatible allowlist; permit wrappers and ordinary libraries; prohibit copied strategy contracts and platform-architecture dependencies. | QMF permits external libraries but owns its domain contracts, so an explicit policy is needed to prevent either blanket bans or contract transplantation. |
| **GAP-0007** — What exact money representation, currency metadata, scale, rounding, and quantization rules apply? | Use `Decimal` or scaled integers with explicit metadata; allow rounding only at named boundaries. | Exact money is directionally agreed, but representation and rounding can invalidate risk arithmetic. |
| **GAP-0008** — How are instants, time zones, trading days, sessions, DST, and FX rollover represented? | Store UTC instants, use venue calendars, and keep civil date and trading date distinct, with a Forex extension. | Exact time is agreed but the encoding and rollover semantics are not. |
| **GAP-0009** — What constitutes stable instrument identity across venues and symbol changes? | Seed identity with venue plus an opaque stable identifier; keep aliases and mutable metadata separate. | Symbols are mutable and can collide, while an asset-neutral core needs stable lineage. |
| **GAP-0010** — What canonical serialization, hash algorithm, fingerprint version, and collision policy apply? | Define versioned canonical bytes, exclude display fields, and include the algorithm identifier in the fingerprint. | Determinism and migration safety require a precisely versioned identity recipe. |
| **GAP-0011** — What is the minimum typed-refusal taxonomy and payload? | Start with invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, and transient venue failure. | Typed refusals are agreed directionally, but agents and adapters cannot interoperate without common cases. |
| **GAP-0012** — What exact result-label tuple prevents mismatched evidence reuse? | Include producer contract version, input fingerprint, run/occurrence identity, and evidence-time range; exclude display names. | These fields bind results to semantics and evidence without making mutable labels part of identity. |
| **GAP-0013** — What latency, throughput, memory, startup, persistence, and recovery budgets apply around the forty-Bot scenario? | First ratify a benchmark scenario, then record numeric p50/p95/p99, sustained/burst throughput, peak RSS, and recovery budgets per component. | The source supports “around forty Bots,” not invented SLO numbers or a fabricated 95th-percentile target. |

### Registry and promotion

| Gap and question | Recommended path — not an answer | Reason |
|---|---|---|
| **GAP-0014** — Which registry object kinds are V1, and what fields does each require? | Use type-specific records sharing only kind, stable id, contract version, created-at, and lineage references. | The universal recipe card is dead; unlike entities must not be forced into one schema. |
| **GAP-0015** — What lineage edges, revision rules, append format, indexes, and compaction policy apply? | Use immutable typed edges such as parent, derived-from, supersedes, promoted-from, and occurrence-of, with rebuildable local indexes. | Graph-shaped history is agreed, while a graph database is explicitly dead. |
| **GAP-0016** — What exact causality/look-ahead registration test and evidence prove a pass? | Require every consumed fact's knowledge time to be no later than decision time; persist input fingerprint, test version, and counterexamples. | A named gate without auditable evidence cannot prevent look-ahead leakage. |
| **GAP-0017** — What does the attempt counter count, at what scope, when does it reset, and how does it constrain research? | Count immutable attempts per declared charter and dataset split; never reset silently; require human approval for a new budget. | Attempt budgets only protect research integrity if their scope and resets are explicit. |
| **GAP-0018** — What is the Bot schema, its confluence cardinality, and its one-Book binding? | Model one-or-more confluences plus one explicit Book-binding reference, subject to the DEC-0040 ruling. | The later correction favors `1..n`, but transcript evidence conflicts and cannot be silently resolved. |
| **GAP-0019** — What evidence and sign-offs permit lab-to-live promotion? | Require artifact fingerprint, lineage, charter, causality pass, untouched-test evidence, risk binding, reviewer identity, and a signed promotion occurrence. | Human-only promotion is law; the immutable evidence bundle is still unspecified. |

### Data, persistence, acquisition, and observability

| Gap and question | Recommended path — not an answer | Reason |
|---|---|---|
| **GAP-0020** — What are the exact qmf-data layer names, responsibilities, schemas, and read/write owners? | Ratify the study responsibilities—ingest, immutable raw archive, processed, journal, split-governed research door, backup—only after schemas and ownership are specified. | The six-layer study was delivered, not adopted; adopting its count prematurely would harden an assistant design. |
| **GAP-0021** — Which store engines and formats serve raw evidence, analytics, registry indexes, journals, and metadata? | Compare candidate formats such as Parquet, DuckDB, SQLite, and JSONL behind QMF-owned contracts; this list selects neither an engine nor journal mutation semantics. | This is a plausible study stack, not a source-ratified engine or history-policy commitment. |
| **GAP-0022** — How are registry and data schemas versioned, migrated, rolled back, and verified? | Require explicit versions, forward migrations, preflight validation, backup, idempotent dry run, post-migration verification, and a non-destructive rollback/recovery specification; do not infer operational restore or cutover. | Silent destructive mutation would violate durability and versioning laws, while operational recovery authority remains in GAP-0027. |
| **GAP-0023** — What bitemporal fact shape preserves event time, knowledge time, source, revision, and corrections? | Require `event_time` and `known_at` for mutable external facts, immutable source/revision identity, and preserved correction records linked to prior revisions. | Look-ahead control and auditability depend on knowing both occurrence and availability time. |
| **GAP-0024** — How are train, validation, and sealed-test splits created, registered, reopened, and audited? | Use time-ordered, non-overlapping fingerprinted split manifests; allow one logged final look at the newest sealed period; never recycle it silently. | Splits-by-default is law, but access and resealing mechanics are absent. |
| **GAP-0025** — Which journal event types, correlation ids, mutation or amendment policy, cadence, retention, and redaction rules are required? | Evaluate candidate event families and history models, including append-only and amendment options, then ratify mutation semantics explicitly before implementation; no option in this row is authorized. | Cross-domain observability is required, but neither an event catalog nor an append-only journal rule is source law. |
| **GAP-0026** — What retention, compaction, partitioning, and capacity rules apply? | Keep source evidence and lineage permanently; partition time series by source, instrument, and bounded window; define compaction after measuring volume. | Full evidence retention is directionally agreed, but operational capacity rules are missing. |
| **GAP-0027** — What backup schedule, encryption, retention, CT-26 completeness and consistency, routine verification, disaster recovery, RTO/RPO, recovery authority, and cutover gate apply? | Compare candidate cadences and providers; define a coherent CT-26 snapshot; and specify routine isolated verification separately from disaster recovery and human-gated cutover. This recommendation authorizes no cadence, restore, recovery, or cutover behavior. | Only the off-machine direction is source law; cadence, verified-restore criteria, recoverability, and operational cutover remain unchosen. |
| **GAP-0028** — Where is the qmf-data adapter boundary versus application-owned download scheduling, retry, and lifecycle? | Let qmf-data own source contracts, normalization, validation, and idempotent ingest; let applications own clocks, schedules, supervision, and UI. | This preserves the toolbox boundary while retaining V1 acquisition plumbing; it still requires explicit ratification. |
| **GAP-0029** — What calendar-provider contract, schedule, dedupe, correction, rate-limit, and legal-retention posture applies? | Persist provider-native identity and revisions through an idempotent recorder, keep scheduling outside QMF, and confirm licence/retention rights before operation. | Calendar capture is a standalone app boundary with legal and correction semantics not yet settled. |
| **GAP-0030** — Which historical/live tick sources, symbols, depth, bid/ask fields, granularity, and reconciliation rules define V1 evidence? | Keep Dukascopy-class history and broker feed separately identified; preserve bid, ask, and source timestamps; retain lineage across disagreements. | The sequence is directionally agreed, but collapsing sources would destroy evidence provenance. |

### Indicators and market structure

| Gap and question | Recommended path — not an answer | Reason |
|---|---|---|
| **GAP-0031** — What indicator protocol defines inputs, alignment, missing values, warm-up, state, streaming, and typed failures? | Define a small deterministic batch-and-incremental protocol with explicit warm-up/missing markers; hide library-specific objects behind adapters. | The wrapper boundary is agreed, but no interoperable protocol exists. |
| **GAP-0032** — Which TA-Lib-class implementation/version is the canonical reference, and how are dual checks recorded? | Pin one reference per release; record inputs, parameters, fingerprints, and tolerances; version arithmetic changes. | Wrapping TA-Lib-class arithmetic does not itself settle canonical output semantics. |
| **GAP-0034** — Which level, zone, and structure families ship first, and what causal confirmation rule applies? | Start with the smallest operator-used causal families, require `observed_at` and `confirmed_at`, and postpone any imprecise family. | qmf-structure is in scope, but family roster and no-look-ahead semantics are not. |

### Venue, secrets, and safe operation

| Gap and question | Recommended path — not an answer | Reason |
|---|---|---|
| **GAP-0035** — What is the complete broker secret lifecycle? | Keep credentials outside repositories/config artifacts, use a protected environment store, document rotation/revocation, and test expiry/compromise recovery. | Venue connectivity crosses a live-money security boundary, yet no lifecycle is specified. |
| **GAP-0036** — Who calls and authorizes a command, what evidence crosses that boundary, and what order state machine, idempotency, reconciliation, retry, outage, and VPS-flattening authority apply? | Keep CT-19 reserved and unwired until the external QMX caller, authorization producer, and authorization evidence are ratified; then evaluate client idempotency, durable observations under the GAP-0025 history policy, uncertainty reconciliation, and explicit flatten authority. | Execution ambiguity is a capital-risk event, and neither an “already-authorized” transport nor implicit retries have a source-ratified contract. |
| **GAP-0037** — Which first broker/account is targeted, and are trend bars bid, ask, mid, or provider-native? | Do not freeze the broker until access is confirmed; preserve native bid/ask and derive mid explicitly. | Broker access is tentative, and derived prices must not masquerade as source evidence. |
| **GAP-0038** — What minimum venue-adapter contract supports later crypto/equities without leaking cTrader into core? | Standardize capability discovery, instrument resolution, subscriptions, execution observations, and typed refusals; reserve command transport until GAP-0036/GAP-0039 assign a caller and authorization-evidence boundary. | Multi-venue extensibility is law, but the seam and command authority are not defined. |

### Book, BMS, exits, and risk arithmetic

| Gap and question | Recommended path — not an answer | Reason |
|---|---|---|
| **GAP-0039** — What Book/BMS schemas, cardinalities, states, versions, and ownership boundaries apply? | Make Book a versioned risk container and BMS a separately versioned policy owned by one Book; leave multiple-BMS support unimplemented pending a ruling. | Risk semantics are in scope, but the detailed dedicated session has not happened. |
| **GAP-0040** — Do Bots own ordinary exits, or does Book own all exit policy and accept Bot exit signals? | Prefer Book-owned policy with mediated Bot exit signals, subject to explicit DEC-0067 ratification. | Repeated direct corrections favor Book ownership, while inherited material conflicts. |
| **GAP-0041** — How does Book-level paper mode map accounts, transition, prevent duplicates, and preserve comparable evidence? | Model an explicit Book state with one active execution destination; record cause/account; prohibit simultaneous live and paper twins. | The ruling survives via the C0022 recap, but transition mechanics and direct wording are missing. |
| **GAP-0042** — What news windows, severity, currency mapping, open-position behavior, and overrides apply? | Keep controls pair-scoped and data-driven; do not freeze the tentative ±15-minute window before evidence review. | Pair scope is strong evidence, but the number was expressed tentatively. |
| **GAP-0043** — What inputs, normalization, thresholds, cadence, hysteresis, and stale behavior define SQS? | Define SQS as a versioned pure function over bid/ask and session context with stale/unavailable outcomes; design the formula fresh. | SQS means Spread Quality Sensor, but its formula was never ratified. |
| **GAP-0044** — What valid formulas replace FORM-0006, and how are R, roster seat, risk allocation, and legacy capital represented? | Start from R as pre-trade risk, give every variable units, keep the capital concepts distinct, and require dimensional tests. | FORM-0006 is dead as dimensionally broken; no replacement is source-backed. |
| **GAP-0045** — What counts as stop-out, what replaces overloaded B/BENCHED names, and what alpha-decay evidence is required? | Define a typed stop-out event, select unambiguous benchmark/roster names, then design fresh alpha-decay math. | The recovered baseline is study-only and legacy formulas are unrecoverable. |
| **GAP-0046** — What same-tick priority applies among stops, force-flat, kill switch, invalidation, and discretionary exits; how does overnight policy apply? | Put venue-confirmed protective execution and emergency controls before discretionary actions, record suppressions, and configure overnight policy per Book. | Concurrent risk actions need deterministic resolution, and the scalping Book is not a universal policy. |

### Study-delivered material that must not be mistaken for an answer

| Ledger item | Delivered study detail | Ratification treatment |
|---|---|---|
| **DEC-0036** | Fingerprint, charter, occurrence, kind-plus-id, and Bot revision model. | Keep candidate-only; answer GAP-0014–GAP-0019 before publishing a registry schema. |
| **DEC-0043** | Six proposed qmf-data layers. | Keep candidate-only; answer GAP-0020 and ownership/schema questions before adopting the count or names. |
| **DEC-0047** | Parquet + DuckDB + SQLite + JSONL local stack. | Use as a discussion starter for GAP-0021, not a selected persistence contract. |
| **DEC-0049** | Automated data/quality detector action. | Keep notification-versus-mutation authority open; study delivery does not grant state-mutation power. |
| **DEC-0094** | Two-stopouts/day baseline, stop-out definition, overloaded B, and BENCHED vocabulary. | Keep invalid as a V1 contract until GAP-0044/GAP-0045 are answered with fresh definitions and units. |
| **Unledgered study catalog** | Answer-key/checklist material accompanying the registry/data studies. | Treat it only as review scaffolding; no checklist field becomes a contract without an operator ruling. [`EXT-0193`–`EXT-0203`] |

## 3. Empty capture points

These are implementation-critical capture slots that the transcripts and manifest do not fully answer. Each remains a question. **Operator prompt for every capture question:** Ratify the recommended path, or name the answer you want.

| Capture question | Related gaps | Recommended path — not an answer | Reason |
|---|---|---|---|
| **Runtime matrix:** Which CPython minor, OS versions, and architectures form the supported matrix? | GAP-0001 | Pin one CPython minor and test the Windows-workstation/Linux-VPS path. | A bounded matrix is necessary for reproducibility; no exact version was chosen. |
| **Stack per component/layer:** Which concrete Python frameworks, runtime libraries, storage clients, and adapter dependencies apply to each of the seven V1 components? | GAP-0001, GAP-0002, GAP-0006, GAP-0021, GAP-0031, GAP-0032, GAP-0035–GAP-0038 | Keep qmf-core free of application/runtime frameworks; choose component-local libraries only after their dependency, persistence, indicator, and venue gaps are ratified. | The sources settle component boundaries and dependency direction, but they do not supply a concrete stack per component. |
| **Local toolchain:** Which formatter, linter, type checker, test runner, coverage gate, and commands are canonical? | GAP-0003 | Choose one opinionated tool per function and publish stable commands. | Agents cannot converge on quality without one executable path. |
| **Build/package layout:** How do the five libraries and two modules map to repositories, packages, build backend, dependency groups, and lockfiles? | GAP-0002 | Use one workspace and one package/component boundary unless a component's module form requires a smaller package. | The roster is authoritative, but packaging is not. |
| **Release/package policy:** How are package and schema versions, compatibility, deprecation, and dependency licences governed? | GAP-0005, GAP-0006 | Version from first release, prohibit silent semantic mutation, and ratify an explicit dependency/licence policy. | The laws state direction but leave operational governance empty. |
| **CI tiers:** What runs at PR, merge, release, scheduled-quality, and disaster-recovery tiers? | GAP-0004, GAP-0027 | Evaluate fast PR gates, integration/contract merge gates, and install/migration release gates; add verification or recovery tiers only after GAP-0027 separately ratifies their purposes and cadence. | The source mandates executable evidence but defines no tier, schedule, restore check, or recovery rehearsal. |
| **Stores and formats:** Which engines/formats own raw, processed, registry, journal, and metadata records? | GAP-0021 | Evaluate the delivered Parquet/DuckDB/SQLite/JSONL stack behind QMF contracts. | Those choices are study-derived and need an explicit operator decision. |
| **Schemas and migrations:** What are the version, migration, rollback, compatibility, and post-migration verification rules? | GAP-0022 | Require explicit schema versions, forward/idempotent migrations, preflight, verification, and a non-destructive rollback/recovery specification; operational recovery and cutover remain separately blocked. | A long-lived foundation cannot rely on destructive in-place mutation, and a migration recommendation is not recovery authority. |
| **Backup and recovery:** What CT-26 snapshot shape, completeness, consistency, schedule, encryption, retention, RPO/RTO, routine-verification procedure, disaster-recovery procedure, and cutover authority apply? | GAP-0020, GAP-0022, GAP-0026, GAP-0027 | Start from the decided off-machine direction, compare candidate schedules and targets, and separately ratify routine verification, recovery, rollback, and human-gated cutover. This captures questions; it authorizes no operation. | Source evidence establishes only off-machine direction, not cadence, verified restore, recoverability, or cutover. |
| **Active lenses:** Should the packet retain `core`, `data`, `ops`, `security`, `observability`, `performance`, `testing`, and `bugs` as active review lenses? | Manifest `lenses` | Keep all eight active for QMF V1. | Every lens maps to an in-scope contract, live-money boundary, durability concern, or factory acceptance gate. |

**Custom-library capture is not empty:** DEC-0024 already fixes the V1 roster at five libraries plus venue and risk modules, so no additional component question is asked here. GAP-0002 still asks how those seven components map to packages and the workspace.

### Lens capture already recorded in the manifest

| Lens | Current scope capture | Reason / handling |
|---|---|---|
| **Data** | **yes** | QMF V1 includes schema-bearing market evidence, lineage, journals, holdout, and backup. |
| **Ops** | **yes** | Venue connectivity, acquisition plumbing, off-machine backup, migration, and recovery/cutover specification cross operational boundaries. |
| **Security** | **yes** | Broker access, secrets, promotion, and live-money authority are in scope. |
| **MLOps** | **no for current scope** | Model training and MIS lifecycle belong to the later trading-node scope; do not create a model registry or training pipeline in QMF V1. |
| **UI** | **no for current scope** | QMX UI and Simulator are explicitly deferred; do not invent screens or UI contracts in this packet. |

## 4. Deaths and supersessions

Deaths remain documented so the factory cannot resurrect them as plausible options.

| Dead decision | Reason it died | Evidence |
|---|---|---|
| **DEC-0014 — third-party strategy-family libraries** | Strategy semantics are QMX-owned; the operator said QMX will build its own. | `EXT-0061`, `EXT-1050` |
| **DEC-0015 — futures/options support** | Permanently excluded; stocks may come later. | `EXT-0063`, `EXT-1058` |
| **DEC-0020 — “minimal core” as whole-project label** | The phrase was retired for the full agreement; qmf-core remains only the first brick. | `EXT-0236` |
| **DEC-0023 — kernel terminology** | It implies an application/runtime center that the operator rejected. | `EXT-0053` |
| **DEC-0034 — universal registry recipe card** | Rejected as too abstract for unlike objects; identity and lineage survive only in principle. | `EXT-0157`, `EXT-0178` |
| **DEC-0037 — graph database in V1** | Graph-shaped lineage does not require Neo4j; the operator answered “No, we don't.” | `EXT-0228` |
| **DEC-0062 — Broker Exam terminology** | “Exam” collides with another concept and must not name broker conformance. | `EXT-0140` |
| **DEC-0063 — connection + parity as one Lock 2 bundle** | Connection was separated; parity belongs to the later backtesting session. | `EXT-0143`, `EXT-0265` |
| **DEC-0069 — parallel Bot paper twins** | No parallel twin; recorded ruling says one Bot binds to one Book. Direct C0022 wording is unavailable. | `EXT-0201`, `EXT-0213`, `EXT-0214` |
| **DEC-0071 — special blackout paper simulator** | Ordinary recorders continue through blackouts, so the special simulator was dropped. | `EXT-0186`, `EXT-0234` |
| **DEC-0073 — Snapshot Quality Sensor interpretation** | Semantic drift; SQS means Spread Quality Sensor. | `EXT-1146` |
| **DEC-0077 — FORM-0006 implementation** | Dimensionally broken and must never be implemented as-is. | `EXT-0071` |
| **DEC-0079 — legacy capital-slot machinery** | Auctions, DPR tables, and slot machinery are donor-only legacy. | `EXT-1151` |
| **DEC-0082 — Program/Campaign machinery** | Rejected as far off; a prop firm is a later Book. | `EXT-0060`, `EXT-0169` |
| **DEC-0084 — central backtesting service** | Cannot provide adequate concurrent compute; future work is modular/on-demand. | `EXT-1089` |
| **DEC-0085 — Nautilus contract adoption** | The operator does not want Nautilus contracts to own the foundation. | `EXT-1093` |
| **DEC-0086 — three-day dependency spike** | Explicitly cancelled. | `EXT-0051`, `EXT-1098` |
| **DEC-0093 — DPR/PRS revival** | Legacy-only; must not return as current risk controls. | `EXT-0256` |

### Supersession chains to preserve

| Superseded | Live successor | Why |
|---|---|---|
| DEC-0010 constrained-only authoring | **DEC-0011 open Python toolbox** | Strictness moved to promotion/live-money boundaries rather than ordinary authoring. |
| DEC-0012 blanket third-party ban | **DEC-0013 build-own boundary** | Suitable dependencies are allowed; QMX retains its own domain contracts and semantics. |
| DEC-0016 QML as framework | **DEC-0017 QMF umbrella / later QML Bot domain** | Naming and scope were corrected. |
| DEC-0018 minimal-core project scope | **DEC-0019 QMF V1 Blueprint** | The full blueprint is the documentation target; qmf-core stays small. |
| DEC-0021 broad runtime kernel | **DEC-0022 definitions-only qmf-core** | Broker, loops, backtest, download, and node runtime moved outside core. |
| DEC-0050 capture excluded | **DEC-0051 acquisition plumbing / first-install bulk history** | Reusable ingest plumbing is V1; scheduling/lifecycle stays application-owned. |

## 5. High-impact laws

These are the ledger entries tagged `law`. They are still **provisional** until the operator signs the Stage 4 decisions.

| Law | Compact rule | Evidence |
|---|---|---|
| **DEC-0001** | Current direct operator rulings outrank conflicting inherited material. | `EXT-0041`, `EXT-1143` |
| **DEC-0002** | GitBook is a Book/BMS baseline; older recovery material is evidence only where later rulings did not change it. | `EXT-0042`, `EXT-0043`, `EXT-1144`, `EXT-1145`, `EXT-1147` |
| **DEC-0003** | Research and delivered studies never auto-adopt into contracts. | `EXT-0040`, `EXT-0203`, `EXT-1046` |
| **DEC-0004** | Document/review QMF before implementation; design one focused topic at a time. | `EXT-0078`, `EXT-0107`, `EXT-1112` |
| **DEC-0006** | Code and docs must be legible to humans and coding agents. | `EXT-0076`, `EXT-1133` |
| **DEC-0007** | Ship no mock market estate, fake Bots, or default strategies; controlled test fixtures are allowed. | `EXT-0090`, `EXT-0111`, `EXT-1104` |
| **DEC-0008** | QMF is a reusable toolbox, not an application. | `EXT-0013`, `EXT-0108` |
| **DEC-0009** | App loops, scheduling, orchestration, and UI stay outside the foundation unless a later contract admits them. | `EXT-0108`, `EXT-0080` |
| **DEC-0011** | Preserve ordinary Python and suitable libraries; enforce uniformity at live-money and harness boundaries. | `EXT-0025`, `EXT-0026`, `EXT-0030`, `EXT-0045`, `EXT-0166` |
| **DEC-0013** | Own QMX domain contracts/strategy semantics; wrappers are allowed without transplanting foreign architecture. | `EXT-0052`, `EXT-0062`, `EXT-0109`, `EXT-1059` |
| **DEC-0017** | QMF is the umbrella; QML is a later Bot-domain library. | `EXT-0083`, `EXT-1026` |
| **DEC-0019** | The documentation target is the QMF V1 Blueprint, not only qmf-core. | `EXT-0235`, `EXT-0237` |
| **DEC-0022** | qmf-core is framework-neutral definitions only—no broker, loop, backtest, download, or node runtime. | `EXT-0095`, `EXT-0112`, `EXT-0118`, `EXT-1131` |
| **DEC-0024** | Final V1 roster: five libraries plus venue and risk modules. | `EXT-0244`, `EXT-0245`, `EXT-0246` |
| **DEC-0030** | Version public contracts from birth; incompatible semantics mint new versions. | `EXT-0114`, `EXT-1134` |
| **DEC-0031** | Core is asset/venue/strategy neutral; Forex/cTrader is only the first consumer. | `EXT-0118`, `EXT-0192`, `EXT-0204` |
| **DEC-0041** | Only a human may promote an artifact into live money. | `EXT-0166`, `EXT-0167` |
| **DEC-0045** | Retain full raw evidence and maintain off-machine backup. | `EXT-0215`, `EXT-0233`, `EXT-1074` |
| **DEC-0046** | Research access uses explicit train, validation, and untouched-test splits by default. | `EXT-0122` |
| **DEC-0054** | Synthetic data may stress systems but may never validate edge. | `EXT-0093`, `EXT-1075` |
| **DEC-0060** | First venue integration is cTrader Open API from Python, not MQL. | `EXT-0141` |
| **DEC-0061** | Venue integration keeps a neutral seam for later crypto/equities. | `EXT-0142`, `EXT-0252` |
| **DEC-0074** | SQS means Spread Quality Sensor and is separate from news control. | `EXT-0069`, `EXT-1138`, `EXT-1146` |
| **DEC-0076** | R is one unit of pre-trade risk, not realized profit/equity/return. | `EXT-0070` |
| **DEC-0080** | The recovered scalping Book is one pattern, not a universal Book law. | `EXT-0073`, `EXT-1139`, `EXT-1140` |
| **DEC-0092** | Design future alpha-decay/benchmark mathematics afresh; do not reconstruct unrecoverable legacy formulas. | `EXT-0264`, `EXT-0270` |
| **DEC-0096** | Every factory-built component ships with executable tests and reference usage. | `EXT-0089` |
| **DEC-0097** | Evolve QMF durably through versioned extension, not repeated foundational rebuilds. | `EXT-0110`, `EXT-1094`, `EXT-1130` |

## 6. Feature inventory in validated shipping order

`_docwork/feature_inventory.yaml` contains **27 planned features** in the dependency-valid order below; `ratified: null`. A blank feature-level `blocked_by` list does **not** waive the blocking `GAP-*` decisions listed in the feature notes. Wave labels come from the validated feature plan. `FEAT-0027` is a fenced reconciliation pass, not permission to implement risk code.

Feature wording is planning scope, not implementation authority. In particular, the inventory adopts no nightly cadence, mandatory verified restore, append-only journal, or already-authorized command transport; each remains explicitly GAP-bound.

| Order | Feature | Size | Wave | Upstream feature blocker(s) and reason | Still-blocking decision gaps |
|---:|---|---|---|---|---|
| 1 | **FEAT-0001 — Money, price, and quantity value contracts** | one-pass | 1 | None; this is the first core slice. | GAP-0001–GAP-0007, GAP-0013; precision/rounding must be ratified, not selected from the recommendation. |
| 2 | **FEAT-0002 — UTC, trading-day, calendar, and session value contracts** | one-pass | 1 | None in inventory; wave-mates sharing `COMP-QMF-CORE` must serialize. | GAP-0001–GAP-0006, GAP-0008, GAP-0013; DEC-0032 keeps exact encoding open. |
| 3 | **FEAT-0003 — Asset-neutral instrument and order-flow nouns** | one-pass | 1 | None in inventory; wave-mates sharing `COMP-QMF-CORE` must serialize. | GAP-0001–GAP-0006, GAP-0009, GAP-0013; identity/alias rules may not be inferred. |
| 4 | **FEAT-0004 — Typed refusal and invariant-violation envelope** | one-pass | 1 | None in inventory; wave-mates sharing `COMP-QMF-CORE` must serialize. | GAP-0001–GAP-0006, GAP-0011, GAP-0013; refusal cases/payload remain open. |
| 5 | **FEAT-0005 — Canonical serialization, fingerprints, and compatibility rules** | one-pass | 2 | FEAT-0001 money, FEAT-0002 time, FEAT-0003 nouns, and FEAT-0004 refusals must exist so canonical bytes cover the complete core surface. | GAP-0001–GAP-0006, GAP-0010, GAP-0012, GAP-0013; result-label tuple remains open. |
| 6 | **FEAT-0006 — Registry identity families and canonical addresses** | one-pass | 3 | FEAT-0005 supplies canonical serialization, fingerprints, and compatibility. | GAP-0002–GAP-0005, GAP-0013, GAP-0014; study kinds/fields are not adopted. |
| 7 | **FEAT-0007 — Registry lineage edges and graph invariants** | one-pass | 4 | FEAT-0006 supplies typed identity families and addresses required by edge endpoints. | GAP-0002–GAP-0005, GAP-0013, GAP-0015, GAP-0021, GAP-0022; reference persistence must not silently select the final engine. |
| 8 | **FEAT-0008 — Causality and look-ahead registration gate** | one-pass | 5 | FEAT-0007 completes the identity/lineage attachment surface for pass and refusal evidence. | GAP-0002–GAP-0005, GAP-0013, GAP-0016; the exact claim and evidence shape must be ruled. |
| 9 | **FEAT-0009 — Immutable registry attempt accounting** | one-pass | 6 | FEAT-0008 supplies the causality outcome/refusal evidence referenced by attempt records. | GAP-0002–GAP-0005, GAP-0013, GAP-0017; target, scope, reset, and budget are open. |
| 10 | **FEAT-0010 — Bitemporal market-fact envelope** | one-pass | 6 | FEAT-0008 supplies the observation/knowledge-time/cutoff identity and evidence contract that facts implement. | GAP-0002–GAP-0006, GAP-0013, GAP-0020, GAP-0023; only a ratified minimum fact shape may land. |
| 11 | **FEAT-0011 — Dataset partition, sealed-holdout, and release contract** | one-pass | 7 | FEAT-0010 supplies fact identity and knowledge time for deterministic membership. | GAP-0002–GAP-0006, GAP-0013, GAP-0024; reopening and audit mechanics remain unresolved. |
| 12 | **FEAT-0012 — Durable operational and research journal-evidence contract** | one-pass | 8 | FEAT-0011 supplies dataset-release and sealed-holdout evidence referenced by research journal entries. | GAP-0002–GAP-0006, GAP-0013, GAP-0025; event types, ids, mutation or append policy, cadence, retention, and redaction are open; durable does not mean append-only. |
| 13 | **FEAT-0013 — Backup snapshot and recovery-boundary specification** | one-pass | 9 | FEAT-0012 completes the fact, dataset-release, and durable journal-evidence contracts covered by backup manifests. | GAP-0002–GAP-0006, GAP-0013, GAP-0026, GAP-0027; provider, encryption, schedule, retention, RTO/RPO, and verification cadence are open, and operational restore/cutover remains blocked. |
| 14 | **FEAT-0014 — Raw-evidence persistence adapter** | one-pass | 10 | FEAT-0013 supplies the fact-integrity, backup-unit, and CT-26/CT-14 boundary contracts the adapter must implement; it does not authorize operational restore. | GAP-0002–GAP-0006, GAP-0013, GAP-0021, GAP-0022, GAP-0026; DEC-0047 does not select an engine. |
| 15 | **FEAT-0015 — Dataset-release access and sealed-holdout enforcement** | one-pass | 11 | FEAT-0014 supplies persisted immutable facts and a backup-safe storage contract. | GAP-0002–GAP-0006, GAP-0013, GAP-0024; override authority/audit mechanics require ratification. |
| 16 | **FEAT-0016 — Journal persistence adapter** | one-pass | 12 | FEAT-0015 supplies sealed-holdout access and override evidence that the journal must persist. | GAP-0002–GAP-0006, GAP-0013, GAP-0021, GAP-0022, GAP-0025, GAP-0026; the study stack is not a backend decision, and no append-only journal rule is adopted. |
| 17 | **FEAT-0017 — Off-machine backup and recovery adapter** | one-pass | 13 | FEAT-0016 completes the settled raw-fact, release, and durable journal stores that the off-machine boundary must protect. | GAP-0002–GAP-0006, GAP-0013, GAP-0026, GAP-0027; only off-machine direction is decided; cadence, provider, encryption, retention, RPO/RTO, recovery, rollback, verification, and cutover are unresolved. |
| 18 | **FEAT-0018 — First historical-source acquisition adapter** | one-pass | 14 | FEAT-0017 ensures new source evidence is admitted only after the raw store, journal, and ratified off-machine protection boundary exist. | GAP-0002–GAP-0006, GAP-0013, GAP-0028, GAP-0030; source/legal/symbol/depth/reconciliation rules are open and bulk download is not part of this pass. |
| 19 | **FEAT-0019 — Incremental indicator protocol and conformance harness** | one-pass | 7 | FEAT-0010 supplies the bitemporal input and derived-fact identity contract. | GAP-0002–GAP-0006, GAP-0013, GAP-0031; GAP-0033 is nonblocking and may only refine light/heavy classification. |
| 20 | **FEAT-0020 — First light-indicator wrapper set** | one-pass | 8 | FEAT-0019 supplies the package-neutral protocol and conformance harness. | GAP-0002–GAP-0006, GAP-0013, GAP-0032; first wrappers and canonical reference/version must be selected explicitly. |
| 21 | **FEAT-0021 — Causal structure-component protocol** | one-pass | 7 | FEAT-0010 supplies the bitemporal fact envelope and causality integration. | GAP-0002–GAP-0005, GAP-0013, GAP-0034; no assistant-generated family taxonomy is adopted. |
| 22 | **FEAT-0022 — First causal structure family** | one-pass | 8 | FEAT-0021 supplies provenance, confirmation, invalidation, and protocol contracts. | GAP-0002–GAP-0005, GAP-0013, GAP-0034; the first family/rules must be ratified before the pass. |
| 23 | **FEAT-0023 — Platform-neutral venue port contract** | one-pass | 9 | FEAT-0012 supplies canonical durable journal evidence for commands, observations, refusals, and reconciliation under the eventual ratified history policy. | GAP-0001–GAP-0006, GAP-0013, GAP-0036, GAP-0038; do not infer a capability set, order state machine, or command authorization boundary. |
| 24 | **FEAT-0024 — cTrader authentication and session adapter** | one-pass | 10 | FEAT-0023 supplies the neutral capability/session/refusal contract. | GAP-0001–GAP-0006, GAP-0013, GAP-0035, GAP-0037; secrets, broker/account, and safe test environment remain open. |
| 25 | **FEAT-0025 — cTrader market-data adapter** | one-pass | 13 | FEAT-0024 supplies authenticated session/capability mapping; FEAT-0016 supplies the durable raw-fact and journal-evidence persistence contracts consumed by received observations. | GAP-0001–GAP-0006, GAP-0013, GAP-0030, GAP-0035, GAP-0037; bid/ask, source, account, and reconciliation rules remain open. |
| 26 | **FEAT-0026 — cTrader order, execution-event, and reconciliation adapter** | one-pass | 14 | FEAT-0025 supplies session, instrument, time, and journal integration, but CT-19 remains reserved and unwired until an external QMX caller and authorization-evidence boundary are ratified. | GAP-0001–GAP-0006, GAP-0013, GAP-0035–GAP-0039; no implementation starts until caller, authorization producer/evidence, and a safe command-state contract are ratified. |
| 27 | **FEAT-0027 — Book, BMS, and risk-boundary specification and reconciliation** | multi-pass | **10 — fenced reconciliation only** | FEAT-0023 supplies the stable venue capability, command, refusal, observation, and reconciliation seam the risk boundary must target. | GAP-0002–GAP-0005, GAP-0007, GAP-0008, GAP-0011, GAP-0013, GAP-0018, GAP-0019, GAP-0025, GAP-0036, GAP-0039–GAP-0046; DEC-0040 and DEC-0067 remain explicit conflicts, so no risk implementation may be scheduled from this row. |

## 7. Full compact ledger

**Count:** 98 entries — 55 provisional, 18 dead, 9 out-of-scope, 8 open, 6 superseded, and 2 conflicts.

| ID | Title | Status |
|---|---|---|
| DEC-0001 | Current operator rulings are authoritative | provisional |
| DEC-0002 | Historical source hierarchy | provisional |
| DEC-0003 | Research never auto-adopts | provisional |
| DEC-0004 | Documentation precedes implementation | provisional |
| DEC-0005 | Project initialization stays with operator tooling | provisional |
| DEC-0006 | Human and agent readability | provisional |
| DEC-0007 | No shipped mock trading estate | provisional |
| DEC-0008 | QMF is a toolbox | provisional |
| DEC-0009 | Application runtime stays outside the foundation | provisional |
| DEC-0010 | Constrained-only authoring surface | superseded |
| DEC-0011 | Open Python toolbox | provisional |
| DEC-0012 | Blanket ban on third-party code | superseded |
| DEC-0013 | Build-own boundary | provisional |
| DEC-0014 | Third-party strategy-family libraries | dead |
| DEC-0015 | Futures and options support | dead |
| DEC-0016 | QML as the framework name | superseded |
| DEC-0017 | QMF umbrella and QML Bot domain | provisional |
| DEC-0018 | Minimal-core project scope | superseded |
| DEC-0019 | QMF V1 Blueprint | provisional |
| DEC-0020 | Minimal core as the whole-project label | dead |
| DEC-0021 | Broad runtime kernel | superseded |
| DEC-0022 | Definitions-only qmf-core | provisional |
| DEC-0023 | Kernel terminology | dead |
| DEC-0024 | Final QMF V1 component roster | provisional |
| DEC-0025 | qmf-core is the first brick | provisional |
| DEC-0026 | Exact money primitives | provisional |
| DEC-0027 | Exact time and trading dates | provisional |
| DEC-0028 | Core market nouns | provisional |
| DEC-0029 | Typed refusals and deterministic fingerprints | provisional |
| DEC-0030 | Versioning from birth | provisional |
| DEC-0031 | Asset-neutral core | provisional |
| DEC-0032 | Six qmf-core freeze choices | open |
| DEC-0033 | qmf-registry V1 boundary | provisional |
| DEC-0034 | Universal registry recipe card | dead |
| DEC-0035 | Graph-shaped lineage without a graph database | provisional |
| DEC-0036 | Registry identity study model | open |
| DEC-0037 | Graph database in QMF V1 | dead |
| DEC-0038 | Content-addressed evidence with two timestamps | provisional |
| DEC-0039 | Bot and Book lineage | provisional |
| DEC-0040 | Bot-to-confluence cardinality | conflict |
| DEC-0041 | Human-controlled promotion | provisional |
| DEC-0042 | qmf-data V1 boundary | provisional |
| DEC-0043 | Six-layer qmf-data study | open |
| DEC-0044 | Historical data retention and sealed holdout | provisional |
| DEC-0045 | Full raw evidence and off-machine backup | provisional |
| DEC-0046 | Research splits by default | provisional |
| DEC-0047 | Proposed local data stack | open |
| DEC-0048 | Cross-domain journal and observability | provisional |
| DEC-0049 | Automatic detector action | open |
| DEC-0050 | Calendar and live-feed capture excluded from foundation work | superseded |
| DEC-0051 | Acquisition plumbing and first-install bulk history | provisional |
| DEC-0052 | Standalone economic-calendar recorder | provisional |
| DEC-0053 | Tick acquisition sequence | provisional |
| DEC-0054 | Synthetic data role | provisional |
| DEC-0055 | qmf-indicators wrapper boundary | provisional |
| DEC-0056 | Light and heavy indicator split | provisional |
| DEC-0057 | Custom indicator discovery | out-of-scope |
| DEC-0058 | qmf-structure boundary | provisional |
| DEC-0059 | Venue module boundary | provisional |
| DEC-0060 | No MQL implementation | provisional |
| DEC-0061 | Multi-venue seam | provisional |
| DEC-0062 | Broker Exam terminology | dead |
| DEC-0063 | Broker connection and parity as one Lock 2 bundle | dead |
| DEC-0064 | Broker parity checklist | out-of-scope |
| DEC-0065 | Risk module boundary | provisional |
| DEC-0066 | Book and BMS are risk semantics | provisional |
| DEC-0067 | Exit ownership | conflict |
| DEC-0068 | Surgical risk controls and correlation | provisional |
| DEC-0069 | Parallel Bot paper twins | dead |
| DEC-0070 | Book-level paper mode | provisional |
| DEC-0071 | Special blackout paper simulator | dead |
| DEC-0072 | Pair-scoped news controls | provisional |
| DEC-0073 | Snapshot Quality Sensor interpretation | dead |
| DEC-0074 | Spread Quality Sensor | provisional |
| DEC-0075 | SQS calculation | open |
| DEC-0076 | R is pre-trade risk | provisional |
| DEC-0077 | FORM-0006 implementation | dead |
| DEC-0078 | Three distinct capital concepts | provisional |
| DEC-0079 | Legacy capital-slot machinery | dead |
| DEC-0080 | Scalping Book is not universal | provisional |
| DEC-0081 | Prop-firm Books | out-of-scope |
| DEC-0082 | Program and Campaign machinery | dead |
| DEC-0083 | Backtesting in QMF V1 | out-of-scope |
| DEC-0084 | Central backtesting service | dead |
| DEC-0085 | Nautilus contract adoption | dead |
| DEC-0086 | Three-day dependency adoption spike | dead |
| DEC-0087 | Future modular backtesting library | out-of-scope |
| DEC-0088 | Trading simulator product | out-of-scope |
| DEC-0089 | MIS as a QMF library | out-of-scope |
| DEC-0090 | QML Bot library in V1 | out-of-scope |
| DEC-0091 | Agentic runtime organs | out-of-scope |
| DEC-0092 | Fresh alpha-decay mathematics | provisional |
| DEC-0093 | DPR and PRS revival | dead |
| DEC-0094 | Recovered benchmark baseline | open |
| DEC-0095 | Multiple BMS per Book | open |
| DEC-0096 | Factory module evidence | provisional |
| DEC-0097 | Long-lived foundation | provisional |
| DEC-0098 | Real workload design target | provisional |
