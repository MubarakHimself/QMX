---
id: DOC-AGENTS
title: QMF V1 Agent Entry Point
type: agents
status: ratified
decisions: [DEC-0099, DEC-0100, DEC-0105, DEC-0106, DEC-0107, DEC-0108, DEC-0109, DEC-0110, DEC-0114, DEC-0115, DEC-0116, DEC-0117, DEC-0119, DEC-0120, DEC-0121, DEC-0122, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0130, DEC-0131, DEC-0132, DEC-0133, DEC-0134, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0140, DEC-0141, DEC-0142, DEC-0143, DEC-0144, DEC-0145, DEC-0146, DEC-0147, DEC-0148, DEC-0149, DEC-0150, DEC-0151, DEC-0152, DEC-0153, DEC-0154, DEC-0155, DEC-0156, DEC-0157, DEC-0158, DEC-0159, DEC-0160, DEC-0161, DEC-0162, DEC-0163, DEC-0164, DEC-0165, DEC-0166, DEC-0167, DEC-0168, DEC-0169, DEC-0171, DEC-0172, DEC-0173, DEC-0174, DEC-0175, DEC-0176, DEC-0177, DEC-0178, DEC-0179, DEC-0180, DEC-0181, DEC-0182, DEC-0183, DEC-0184, DEC-0185]
sources: [docs/constitution.md, docs/architecture/overview.md, docs/architecture/dependencies.yaml, docs/architecture/stack.md, docs/registry/variables.yaml, docs/contracts/, docs/components/, docs/decisions/, docs/gap-report.md, docs/scenarios/, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-21
stale_after: 30d
---

# AGENTS.md — Read This First

QMF V1 is a reusable Python toolbox from which QMX trading applications will be built; it is not itself a trading application. Its fixed public roster is five libraries plus the Venue and Risk modules, with internal data seams and external providers kept distinct; market-hours calendar extensions (the first is `COMP-QMF-CALENDAR-FOREX`) live in the workspace but outside that roster, on their own SemVer ladder. The first application-layer product built on that toolbox — `COMP-QMB`, the QMX experimentation/backtesting library plus the `qmb` CLI ([`docs/components/qmb.md`](components/qmb.md)) — now realizes the glossary's reserved future-backtesting-library slot; it consumes QMF contracts without redefining them (the AD-29..41 vocabulary is read-only to it) and produces its evidence through them in `world = replay`, is a `library` and a `CLI` (never an "engine" or a "kernel") built ON QMF, and is not a roster package (DEC-0159, DEC-0169). This knowledge base is **operator-ratified design** — corpus signed off by the operator 2026-08-21 (conditional go-ahead in the PRD session; the independent contradiction sweep passed). Ratified status is documentation authority only, never implementation or live-operation authority: implementation authorization arrives exclusively through the factory pipeline.

The **foundation, the indicators/structure increment, the venue increment, and the risk increment are now operator-ratified**. The 2026-08-19/20 foundation architecture sitting ratified the spine AD-1 through AD-21 (ledger DEC-0099 through DEC-0125); the 2026-08-20 indicators/structure increment ratified AD-22 through AD-25 (ledger DEC-0126 through DEC-0134); the 2026-08-20 venue architecture sitting ratified AD-26 through AD-28 (ledger DEC-0135 through DEC-0142); the 2026-08-20 risk architecture sitting ratified AD-29 through AD-41 with cross-AD amendments (ledger DEC-0143 through DEC-0158); the 2026-08-20 QMB architecture sitting ratified the QMB spine B-1 through B-15 by operator delegation (ledger DEC-0159 through DEC-0169: thin doors, the config compiler, the pure-run/impure-orchestrator split, reader-derived verdicts, CT-32/CT-13 adoption, fidelity seams with the optimistic taint, registry as-of sets — implementation still factory-pipeline-only); and the 2026-08-21 QML increment ratified the QML spine QL-1 through QL-10 by operator delegation (ledger DEC-0171 through DEC-0184, veto round DEC-0185: the bot-authoring library, the two-artifact bot with the `.qml` DSL not revived, CT-33/CT-34 minted as qmf-registry kinds, the bot runtime protocol with its advisory stop proposal, the two-layer conformance gate, and the CT-22/CT-23 format-version-2 mints — answering GAP-0047, implementation still factory-pipeline-only). Together they answer 45 gaps, partially close GAP-0048, and no blocking gap remains open. The rulings are authoritative, and the whole knowledge base was re-ratified by the operator's corpus sign-off of 2026-08-21 — documents now carry `status: ratified`. An answered gap is an operator ruling, never on its own implementation or live-money authority. See [`gap-report.md`](gap-report.md) for what is answered and deferred.

## What is ratified vs still open

- **Ratified foundation content** (build against it as the source of truth): exact money (AD-7, DEC-0105), exact time and calendar rule sets (AD-8, DEC-0106), instrument/venue/account identity (AD-9, DEC-0107), the `fp1` fingerprint recipe (AD-10, DEC-0108), typed refusals (AD-11, DEC-0109), the result label and worlds (AD-12, DEC-0110); packaging and runtime (AD-1/AD-2), toolchain and gates (AD-3/AD-4), version ladders (AD-5), dependency tiers (AD-6); performance/observability/concurrency (AD-13/AD-14/AD-15); registry per-kind records, multiplicity, and the promotion skeleton (AD-16/AD-17/AD-18, DEC-0114/DEC-0115/DEC-0116); data rooms, migrations, backup primitives, and splits/journal/adapters (AD-19/AD-20/AD-21, DEC-0117/DEC-0118/DEC-0119); the two-mode indicator protocol and series vocabulary/BarSpec (AD-22, DEC-0126), canonical TA-Lib 0.7.1 arithmetic (AD-23, DEC-0127), the light/heavy four-bound rule (AD-24, DEC-0128, superseding DEC-0056), and the causal structure lifecycle (AD-25, DEC-0129).
- **Ratified venue content** (build against it as the source of truth): the cTrader venue facts and their per-broker measured obligations (DEC-0135, superseding DEC-0123), the secret lifecycle of references-not-values (AD-26, DEC-0136), the four-command vocabulary and the four-outcome uncertainty law where `UNKNOWN` is a state and `denied-locally` is an outcome (AD-27, DEC-0137), the one-port four-contract adapter with static capability declaration versus per-account venue-observation profile and market data homed at CT-10/CT-15 (AD-28, DEC-0138), broker identity as deployment configuration (DEC-0139), and the venue and cross-AD amendments (DEC-0140, DEC-0141). The qmf-venue design is ratified; connectivity authorizes nothing on its own, and implementation authorization arrives only through the factory pipeline.
- **Ratified risk content** (build against it as the source of truth): the Book/BMS binding chain with the BMS as the account-facing supervising layer — one BMS instance per account serving many Books, a Book binds exactly one BMS, a Bot binds exactly one Book (AD-29, DEC-0143); templates as configuration artifacts with per-variable ui-editable/uneditable flags and git-logic versioning (AD-30, DEC-0144); journals-as-projections (AD-31, DEC-0145); three-layer admission with no probation (AD-32, DEC-0146); Book-owned exit policy with Bot proposals through the CT-23 door (AD-33, DEC-0147, resolving DEC-0067); `amend_protection` as the fifth venue command (AD-34, DEC-0148); paper as a Book-level standing evidence state (AD-35, DEC-0149, confirming DEC-0070); control actions with the kill switch (global) versus kill line (per-Book floor) split (AD-36, DEC-0150); same-tick priority per command stream (AD-37, DEC-0151); one protection-window contract for news, dead zone, and handover buffers (AD-38, DEC-0152); SQS V1 as a block-only CT-16 configured producer (AD-39, DEC-0153); the R/numeraire/dimensional law with USD numeraire (AD-40, DEC-0154); and the exit-record, bench fold, and `venue_liquidation` vocabulary split (AD-41, DEC-0155). Every number the sitting recovered is a configurable UI-editable variable with recorded evidence and no ratified spine value (DEC-0157); risk contracts CT-22 through CT-25 and CT-27 through CT-32 are `defined-unwired` surface, and implementation authorization arrives only through the factory pipeline.
- **Ratified QML content** (build against it as the source of truth): QML is the QMX bot-authoring application-layer library built ON QMF — one uv-installable pure distribution (`import qml`), never a roster package, framework, or engine (AD-2/L11, DEC-0171); a governed bot is exactly two artifacts — the CT-33 Bot definition declaration plus plain-Python logic conforming to the bot runtime protocol — with the `.qml` DSL not revived in V1 (DEC-0172); the CT-33 Bot definition kind fills AD-16's reserved Bot kind and the CT-34 confluence kind carries one-or-more legs of roles `level | trigger | confirmation | filter` (DEC-0173, DEC-0175); the footprint is the single canonical consumption manifest with pinned-or-template producer bindings (DEC-0174); a strategy family is a key with no authority, exactly one per bot (DEC-0176); the bot runtime protocol carries an optional advisory stop proposal while the declared full-loss price stays Book-resolved (DEC-0177); the conformance gate is technical never performance — two layers plus a ticket that gates evidence citation and Book seats, never tunnel entry — with the four-check prediction linter filling AD-32's Layer-1 slot (DEC-0178); exit reconciliation ratifies AD-33's donor atoms as-is with CT-29 the one close-reason taxonomy (DEC-0179); QML builds before the trading node and may build alongside QMB, own SemVer display-only (DEC-0180). CT-33/CT-34 mint as qmf-registry kinds, CT-06 updates for the Bot kind body and the strategy-family record kind, and CT-22/CT-23 take AD-5 format-version-2 mints with migration notes (DEC-0181, DEC-0182); GAP-0047 is answered (DEC-0184). The design is ratified by operator delegation 2026-08-21; implementation authorization arrives only through the factory pipeline, and COMP-QML is ratified design surface (corpus sign-off 2026-08-21).
- **Still open** — none blocking. Deferred: the look-ahead **gate** and attempt counter (GAP-0016/GAP-0017, DEC-0121) — the 2026-08-20 QMB sitting delivered look-ahead *prevention* by construction (B-2/B-8/B-12, DEC-0169) while the registration gate itself stays deferred; the fidelity-content sitting (GAP-0048 partially closed — seams ruled per DEC-0164, taxonomy values and calibration content still open); and the research-threshold sitting (GAP-0049). GAP-0047 (QML) is now **answered** — the 2026-08-21 QML increment absorbed the bot-authoring library (DEC-0171 through DEC-0184). `world = simulated` stays reserved-unusable until GAP-0048 rules the fidelity taxonomy and calibration content (DEC-0110, DEC-0164).
- **Node-material boundary** (DEC-0142): trading-node runtime material stays out of QMF documentation. The order path, protection funnel, startup semantics, and flatten-authority assignment are node/risk-sitting territory; QMF records only the contract surface AD-26 through AD-28 define and references [`tracker/trading-node-notes.md`](../tracker/trading-node-notes.md) as a pointer, never absorbing it.

## Reading order

1. [`docs/constitution.md`](constitution.md) — the laws; violating one is a bug by definition.
2. [`docs/architecture/overview.md`](architecture/overview.md) — system context, component boundaries, and layers.
3. [`docs/gap-report.md`](gap-report.md) — the 45 answered gaps, the deferred gaps (no conflict remains live), the graveyard, and out-of-scope standing.
4. The spec for every component you will touch in [`docs/components/`](components/).
5. Every boundary named by those specs in [`docs/contracts/`](contracts/).
6. [`docs/registry/variables.yaml`](registry/variables.yaml) for values and [`docs/glossary.md`](glossary.md) for terminology.
7. The applicable ADRs in [`docs/decisions/`](decisions/) and scenarios in [`docs/scenarios/`](scenarios/).

Do not start with a transcript or a study recommendation. The reference docs and their explicit GAP markers are the execution boundary.

## Hard rules

- Later direct operator corrections govern conflicting historical material; research remains evidence until adopted. See [L1–L3](constitution.md#laws).
- Documentation and review precede code generation or trading-node implementation. See [L4](constitution.md#laws).
- QMF is a toolbox, not an application: loops, scheduling, orchestration, and product UI stay outside it. See [L7–L8](constitution.md#laws).
- qmf-core is definitions-only and asset-neutral; broker, runtime, download, backtest, and node behavior do not belong there. See [L13 and L16](constitution.md#laws).
- The public roster remains five libraries and two modules. Internal seams do not become public packages by implication; market-hours calendar extensions live outside the roster on their own SemVer ladder. See [L14](constitution.md#laws) and DEC-0100.
- **Default-deny dependency direction.** `qmf-core` depends on nothing; every package may depend on `qmf-core`; nothing imports `qmf-venue` or `qmf-risk`. No package may depend on any package other than `qmf-core` until an inter-library edge is ratified as a spine amendment. Exactly one edge is ratified: `qmf-registry → qmf-data`. This rule is **roster-scoped** — it governs the seven roster packages internally; an application-layer product built on the workspace (QMB, QML) may consume qmf-risk (and any qmf-venue-free) contracts at its own composition root, per the ratified reading (DEC-0171, DEC-0184; QMB precedent DEC-0169). Applications still never import `qmf-venue`. See [L30](constitution.md#laws) and DEC-0120.
- **Three-calendar naming rule.** Never write bare "calendar". Three distinct named concepts exist: the **market-hours calendar** (session schedule + accounting rollover, e.g. `COMP-QMF-CALENDAR-FOREX`), the **day-boundary calendar** (an account-scoped accounting-boundary rule), and the **news calendar** (`COMP-CALENDAR-FEED`, the external event feed). They are never substituted for one another. See DEC-0106 (AD-8).
- Everything downstream of QMF — the trading node, backtesting, the agentic system, and the UI — is built with QMF libraries and must not re-implement or bypass its contracts. See [L31](constitution.md#laws) and DEC-0122.
- Banned vocabulary: say **extensions** not "plugins"; backtesting is a **library**, never an "engine"; the retired terms "kernel" and "exam" (broker conformance) must not return; say **as-of set**, never "snapshot", for registry state (DEC-0165). See the [graveyard](gap-report.md#dead-decisions--18).
- Public contracts are versioned from birth; incompatible meaning mints a new version. See [L15](constitution.md#laws).
- Only a human may promote an artifact into the live zone. See [L17](constitution.md#laws).
- Preserve complete raw evidence, keep the off-machine direction, and expose research data through explicit splits. See [L18–L19](constitution.md#laws).
- Synthetic data may test infrastructure and failures, never trading edge. See [L20](constitution.md#laws).
- The first Venue target is the cTrader Open API from Python, never MQL, behind a venue-neutral seam. See [L21–L22](constitution.md#laws).
- Provisional contracts, recommendations, and unresolved GAPs authorize neither implementation nor live money. Destructive and live actions require a ratified contract and explicit human authority. See [L29](constitution.md#laws).
- Never revive a dead decision. Check the [graveyard](gap-report.md#dead-decisions--18) before proposing a component, service, formula, or term that resembles old material.

## Before changing anything

1. Identify each affected `COMP-*` ID in [`dependencies.yaml`](architecture/dependencies.yaml).
2. Use the documentation-factory skill's `scripts/blast_radius.py`, passing the component ID and `--root .`; read every document it returns.
3. Read the component's `depends_on` and interface list. Every `CT-*` must resolve in [`docs/contracts/`](contracts/), and every peer must exist in the dependency manifest.
4. Read [`variables.yaml`](registry/variables.yaml). Never hardcode or restate a value that has a `registry:*` key; a null value remains unresolved.
5. Search [`gap-report.md`](gap-report.md) for every relevant component, contract, and term. A blocking gap means the affected behavior is not buildable.
6. Read the applicable scenario. A scenario labelled **blocked specification** is not complete, test-complete, releasable, or permission to fill placeholders.
7. Record any approved change in a new ADR and in [`changelog.md`](changelog.md). Do not mutate an existing ADR to rewrite history.

## Architecture preflight — before building anything new

Answer these items in the plan and the new ADR before writing code for a component, service, module, table, endpoint, adapter, or package.

1. **Read the inventory.** Cite [`dependencies.yaml`](architecture/dependencies.yaml), [`stack.md`](architecture/stack.md), and every plausible existing component spec.
2. **Prove reuse-or-new.** For each candidate component, state the exact authority boundary or contract mismatch that prevents reuse. If an existing component can own the behavior, extend it and stop.
3. **Keep the axes separate.** `layer`, `kind`, `roster_role`, and `distribution` mean different things. Distribution is ratified (DEC-0100): the seven roster packages are `uv-workspace-lockstep`; calendar extensions are `separate-versioned-package-own-semver` outside the roster.
4. **If new is required,** state what unique authority it owns, what it may never do, every contract at its boundary, and which existing authority becomes narrower.
5. **Check the graveyard.** A dead decision ends reuse of that idea unless a later operator ruling explicitly replaces it.
6. **Record the verdict.** Write `reuse COMP-<NAME>` or `new COMP-<NAME>` and the evidence in the ADR. An unrecorded verdict means the preflight did not happen.

## Change protocol

Before modifying component X:

1. Run blast-radius analysis for X and every directly affected peer.
2. Read the constitution, dependency manifest, target specs, contracts, registry entries, ADRs, gaps, and scenarios returned by the analysis.
3. Confirm that each prerequisite decision is ratified and every blocking gap for the slice is answered. A recommendation is not an answer.
4. Draft a new ADR with the architecture-preflight verdict and contract/version impact.
5. Update reference docs, registry/contracts, scenarios, gap status, index, and changelog in the same change.
6. Run the documentation-factory validators and do not report success while citations, graph alignment, or non-provisional release gates fail.

## Where answers live

| Question | Canonical document |
|---|---|
| What may never be violated? | [`constitution.md`](constitution.md) |
| What components exist and how do they connect? | [`overview.md`](architecture/overview.md) and [`dependencies.yaml`](architecture/dependencies.yaml) |
| What does a component own or refuse to own? | Its file in [`components/`](components/) |
| What crosses a boundary? | The matching file in [`contracts/`](contracts/) |
| What is the exact value? | [`registry/variables.yaml`](registry/variables.yaml) |
| Why was a direction chosen? | [`decisions/`](decisions/) and the decision locator in [`index.md`](index.md) |
| What is undecided, dead, deferred, or out of scope? | [`gap-report.md`](gap-report.md) |
| What behavior should a future test demonstrate? | [`scenarios/`](scenarios/) and [`fixtures-and-scenarios.md`](lenses/testing/fixtures-and-scenarios.md) |
| What changed in the knowledge base? | [`changelog.md`](changelog.md) |

## Current release gate

The corpus was signed off by the operator on 2026-08-21 (conditional go-ahead in the PRD session; the independent contradiction sweep passed) and documents now carry `status: ratified`. Ratified documentation alone still authorizes no QMF implementation, live venue connection, order submission, paper-mode transition, operational restore, destructive migration, or release-quality acceptance claim — implementation authorization arrives exclusively through the factory pipeline. The foundation, indicators/structure, venue, and risk sittings answered 44 gaps (DEC-0099–DEC-0119, DEC-0126–DEC-0129, DEC-0135–DEC-0138, and DEC-0143–DEC-0155), the 2026-08-21 QML increment answered a 45th — GAP-0047 (DEC-0171–DEC-0184) — the exit-ownership conflict (DEC-0067) is resolved (DEC-0147), DEC-0049 was ruled at sign-off (scoped entry-blocking detector pause, EXT-2093), and no blocking gap remains open. The deferred items (GAP-0016/GAP-0017, GAP-0048, GAP-0049) await their own sittings and stay non-authorizing.
