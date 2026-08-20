---
id: COMP-QMF-RISK
title: QMF Risk Module
type: component-spec
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0039, DEC-0041, DEC-0048, DEC-0065, DEC-0066, DEC-0068, DEC-0070, DEC-0072, DEC-0074, DEC-0076, DEC-0078, DEC-0080, DEC-0092, DEC-0094, DEC-0095, DEC-0101, DEC-0105, DEC-0107, DEC-0109, DEC-0111, DEC-0112, DEC-0113, DEC-0115, DEC-0116, DEC-0119, DEC-0120]
sources: [DEC-0039, DEC-0040, DEC-0041, DEC-0048, DEC-0065, DEC-0066, DEC-0067, DEC-0068, DEC-0070, DEC-0072, DEC-0074, DEC-0076, DEC-0078, DEC-0080, DEC-0092, DEC-0094, DEC-0095, DEC-0101, DEC-0105, DEC-0107, DEC-0109, DEC-0111, DEC-0112, DEC-0113, DEC-0115, DEC-0116, DEC-0120, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/ct-01-money-quantity.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-25-risk-journal.yaml, _docwork/feature_inventory.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF Risk Module

`COMP-QMF-RISK` is a fenced provisional boundary for reusable Book, BMS, money-management, and risk semantics. It is not implementation-ready: FEAT-0027 must reconcile the Book/BMS vocabulary, Bot binding, exit ownership, modes, formulas, controls, priorities, and node boundary before this component is decomposed into buildable slices. [DEC-0065] [DEC-0066] [DEC-0095]

## Authority boundary

May, after the fenced reconciliation and contract wiring are ratified: express versioned Book and BMS risk semantics; consume exact QMF values and source observations; represent lineage and registration evidence; evaluate only the reusable risk rules assigned to QMF; and reserve Book-level mode and journal-evidence shapes. CT-22 through CT-25 have no active caller or consumer. [DEC-0039] [DEC-0065] [DEC-0066]

May never: implement trading-entry logic; run a trading-node loop; connect to a venue; write a physical store; promote an artifact into live money without a human; hardcode Bot/confluence cardinality against the ratified one-or-more multiplicity, or invent exit ownership; treat the recovered Scalping Book as universal; revive the dead parallel-Bot paper-twin design; or revive the dead FORM-0006, DPR, PRS, auctions, or legacy slot machinery. [DEC-0115] [DEC-0041] [DEC-0067] [DEC-0069] [DEC-0077] [DEC-0079] [DEC-0080] [DEC-0093]

This provisional spec reserves contracts only. It grants no permission to implement risk decisions, authorize orders, transition accounts, connect to live money, or infer answers from recommendations.

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Exact money, price, and quantity values | in | [CT-01](../contracts/ct-01-money-quantity.yaml) | COMP-QMF-CORE |
| Exact time and trading-calendar values | in | [CT-02](../contracts/ct-02-time-calendar.yaml) | COMP-QMF-CORE |
| Instrument and venue identity | in | [CT-03](../contracts/ct-03-instrument-identity.yaml) | COMP-QMF-CORE |
| Typed refusals | out | [CT-04](../contracts/ct-04-typed-refusal.yaml) | COMP-QMF-CORE |
| Version, fingerprint, and compatibility values | in/out | [CT-05](../contracts/ct-05-version-fingerprint.yaml) | COMP-QMF-CORE |
| Registry registration | out | [CT-06](../contracts/ct-06-registration.yaml) | Owned by COMP-QMF-REGISTRY; application-mediated, not an import edge [DEC-0120] |
| Lineage edges | out | [CT-07](../contracts/ct-07-lineage-edge.yaml) | Owned by COMP-QMF-REGISTRY; application-mediated, not an import edge [DEC-0120] |
| Source observations (values supplied by the application) | in | [CT-10](../contracts/ct-10-source-observation.yaml) | Owned by COMP-QMF-DATA; application-mediated, not an import edge [DEC-0120] |
| Journal evidence | out (reserved) | [CT-13](../contracts/ct-13-journal.yaml) | Intended: COMP-QMF-DATA; not wired |
| Reserved Book and BMS charter | out (reserved) | [CT-22](../contracts/ct-22-book-charter.yaml) | Intended: COMP-QMF-REGISTRY; not wired |
| Reserved risk evaluation and refusal; caller unassigned | in/out (reserved) | [CT-23](../contracts/ct-23-risk-evaluation.yaml) | No active or intended consumer assigned |
| Reserved Book-mode evidence | out (reserved) | [CT-24](../contracts/ct-24-book-mode.yaml) | Intended: COMP-QMF-REGISTRY, COMP-QMF-DATA; not wired |
| Reserved risk and Book journal evidence | out (reserved) | [CT-25](../contracts/ct-25-risk-journal.yaml) | Intended: COMP-QMF-DATA; not wired |

## Behavior

Book and BMS represent risk, money management, and position-sizing policy, not trading-entry logic. The recovered Scalping Book is one reusable pattern and does not define every Book. [DEC-0066] [DEC-0080]

The meaning of R is defined only by `registry:original_risk_unit`; this spec does not restate that non-null registry value or substitute realized-profit, equity, or post-trade-return semantics for it. [DEC-0076]

News control is pair-scoped and separate from SQS. SQS means Spread Quality Sensor. Exact windows and the SQS formula remain unresolved at `registry:news_blackout_before`, `registry:news_blackout_after`, and `registry:spread_quality_sensor_formula`. [DEC-0072] [DEC-0074] [DEC-0075]

The parallel Bot paper-twin design cited by DEC-0069 is dead. A study recap records a Book-level, one-Bot-to-one-Book paper-mode direction, but the direct operator wording is missing from `SRC-01-C0022`; this is evidence only, not an executable ruling or transition. CT-24 remains reserved until the operator confirms the recap and GAP-0041 defines transition and account semantics. [DEC-0069] [DEC-0070]

### Bot, Book, and account binding

Bot/confluence multiplicity is ratified, resolving the former DEC-0040 conflict: a Bot contains one-or-more confluences, and no layer of the bot vocabulary hardcodes exactly-one — the rule generalizes recursively (a confluence contains one-or-more levels, triggers, and confirmations; components may compose, a composite being its own artifact with lineage to its children). [DEC-0115]

Bot identity is its content. The Bot-Book-account binding is a separate dated binding record outside Bot identity: one Bot is bound to exactly one Book at any time, and re-binding (paper to live) never mints a new Bot, so paper and live performance stay comparable for alpha-decay sensing. [DEC-0115]

Books bind to accounts. An account carries a role (live, demo, paper-validation, paper-benched, or prop-firm), and Venue and Account are first-class nouns defined in `COMP-QMF-CORE` with their records owned by `COMP-QMF-REGISTRY`. The full Bot and Book schemas remain their own sittings. [DEC-0107]

### Foundation invariants

QMF values are immutable and safe to share by construction; QMF never spawns threads or background work — the application owns all concurrency, and async APIs exist only at the venue network edge, never in this module. [DEC-0113] Money, Price, and Quantity are scaled integers on the money path that binds risk (position sizing, R, P&L): binary float is banned there and crosses back only at named conversion boundaries with an explicitly stated rounding mode. [DEC-0105]

Every public operation succeeds or returns a CT-04 typed refusal carrying context and retryability; refusals are never swallowed. A `correlation_id` propagates across every package boundary, and the module exposes a no-argument `health()` returning a typed report. [DEC-0112] The module ships a benchmark harness measuring speed and peak memory at a framework-native load ladder, gated at tier 2 alongside speed. [DEC-0111] QMF's own source is governed by ruff, pyright strict, and pytest, shipping executable tests and reference usage as tier-1 artifacts. [DEC-0101]

Package dependency is default-deny: the module imports only `COMP-QMF-CORE`, and nothing imports the module. Registration, lineage, and journal evidence reach the registry and `qmf-data` through the application composition root — never a direct `qmf-risk` import of a sibling. Adding an inter-library edge is a spine amendment. [DEC-0120]

`GAP(GAP-0039): Define Book and BMS fields, ownership, lifecycle, version compatibility, and BMS multiplicity; DEC-0095 remains open.`

`GAP(GAP-0040): Resolve whether Book owns every exit policy or mediates ordinary Bot exits; DEC-0067 remains a conflict.`

`GAP(GAP-0041): Define Book live/paper states, accounts, triggers, duplicate prevention, continuity, rollback, and audit evidence.`

`GAP(GAP-0042): Define pair-scoped news windows, severities, mappings, open-position behavior, and overrides.`

`GAP(GAP-0043): Define SQS inputs, units, formula, thresholds, cadence, hysteresis, and stale-data behavior.`

`GAP(GAP-0044): Replace dead FORM-0006 with dimensionally valid formulas and distinct capital concepts.`

`GAP(GAP-0045): Define stop-out, benchmark/roster terminology, bench behavior, and fresh alpha-decay evidence.`

`GAP(GAP-0046): Define deterministic same-tick priority and Book-specific overnight behavior.`

<!-- no-diagram: Book/BMS structure and every risk state machine are intentionally fenced by FEAT-0027 and GAP-0039 through GAP-0046; a diagram would invent states or ownership -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| R definition | `registry:original_risk_unit` | Registry-held meaning only; this spec does not restate the non-null value. |
| News blackout before event | `registry:news_blackout_before` | Null until GAP-0042 ratifies a duration and mapping semantics. |
| News blackout after event | `registry:news_blackout_after` | Null until GAP-0042 ratifies a duration and mapping semantics. |
| Spread Quality Sensor formula | `registry:spread_quality_sensor_formula` | Null until GAP-0043 ratifies inputs, units, and arithmetic. |
| Bench stop-out threshold | `registry:bench_stopout_threshold` | Null until GAP-0045 defines stop-out and bench state. |
| Bench reset boundary | `registry:bench_reset_boundary` | Null until GAP-0045 defines reset behavior. |
| Monetary representation and rounding | `registry:monetary_representation`, `registry:money_rounding_mode` | Scaled integers at a declared scale on the money path; binary float is banned there and crosses back only at named conversion boundaries with an explicit rounding mode. [DEC-0105] |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A caller requests risk evaluation through CT-22 or CT-23. | No caller or consumer is wired, so no risk decision or authorization may be produced. `GAP(GAP-0039): Complete the fenced reconciliation and assign the contract wiring first.` | DEC-0065, DEC-0066 |
| FM-2 | A request depends on unresolved exit ownership. | No exit policy may be inferred or routed. `GAP(GAP-0040): Resolve DEC-0067 before implementation.` | DEC-0067 |
| FM-3 | A formula or payload uses dead FORM-0006, DPR, PRS, auctions, or legacy capital slots. | The input is inadmissible and cannot enter CT-23; it returns a `policy rejection` refusal from the ratified seven-category taxonomy. | DEC-0077, DEC-0079, DEC-0093, DEC-0109 |
| FM-4 | A proposed paper transition would revive the dead parallel-Bot paper-twin design cited by DEC-0069. | No transition implementation exists: CT-24 remains evidence-only until operator confirmation and GAP-0041 defines states, triggers, duplicate prevention, continuity, rollback, and evidence. | DEC-0069, DEC-0070 |
| FM-5 | A promotion or live-mode transition lacks human authorization. | The component must not promote or activate the artifact; promotion is a human-only signed occurrence card whose mandatory plain-words summary is an identity field, and the journal's promotion event carries only that card's fingerprint. The evidence checklist still accretes from the data, backtesting, and risk sittings, and the gate itself is platform territory. | DEC-0041, DEC-0116 |
| FM-6 | SQS, news, stop-out, alpha-decay, or priority inputs are missing, stale, or ambiguous. | No formula or transition may be invented. The governing GAP-0042 through GAP-0046 marker remains the behavior boundary. | DEC-0072, DEC-0074, DEC-0092, DEC-0094 |
| FM-7 | An implementation assumes CT-25 already hands evidence to qmf-data. | The assumption is invalid: CT-25 is reserved and unwired, and the component must not write a physical store directly; risk-transition events are one of the seven ratified journal event types carried in gapless per-writer streams (DEC-0119), and any handoff to qmf-data goes through the application composition root under default-deny, never a direct store write (DEC-0120). | DEC-0048, DEC-0065, DEC-0119, DEC-0120 |
| FM-8 | One Book is assigned several BMS policies without a ratified multiplicity rule. | The component must not select or merge them. `GAP(GAP-0039): Resolve DEC-0095.` | DEC-0095 |

## Related

Decisions: DEC-0039, DEC-0041, DEC-0048, DEC-0065, DEC-0066, DEC-0067, DEC-0068, DEC-0070, DEC-0072, DEC-0074, DEC-0076, DEC-0078, DEC-0080, DEC-0092, DEC-0094, DEC-0095, DEC-0105, DEC-0107, DEC-0115, DEC-0116. Superseded: DEC-0040 (Bot-to-confluence cardinality) is resolved by DEC-0115. Dead decisions: DEC-0069, DEC-0077, DEC-0079, DEC-0093. Scenarios: [SCN-0005 uncertain venue submission](../scenarios/SCN-0005-uncertain-venue-submission.md), [SCN-0006 Book paper transition](../scenarios/SCN-0006-book-paper-transition.md), [SCN-0007 human promotion](../scenarios/SCN-0007-human-promotion.md), [SCN-0008 pair-scoped news](../scenarios/SCN-0008-pair-scoped-news.md), [SCN-0010 risk conflicts](../scenarios/SCN-0010-risk-boundary-conflicts.md). Knowledge: none drafted.
