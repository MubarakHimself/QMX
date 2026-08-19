---
id: COMP-QMF-RISK
title: QMF Risk Module
type: component-spec
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0039, DEC-0041, DEC-0048, DEC-0065, DEC-0066, DEC-0068, DEC-0070, DEC-0072, DEC-0074, DEC-0076, DEC-0078, DEC-0080, DEC-0092, DEC-0094, DEC-0095]
sources: [DEC-0039, DEC-0040, DEC-0041, DEC-0048, DEC-0065, DEC-0066, DEC-0067, DEC-0068, DEC-0070, DEC-0072, DEC-0074, DEC-0076, DEC-0078, DEC-0080, DEC-0092, DEC-0094, DEC-0095, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/ct-01-money-quantity.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-25-risk-journal.yaml, _docwork/feature_inventory.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF Risk Module

`COMP-QMF-RISK` is a fenced provisional boundary for reusable Book, BMS, money-management, and risk semantics. It is not implementation-ready: FEAT-0027 must reconcile the Book/BMS vocabulary, Bot binding, exit ownership, modes, formulas, controls, priorities, and node boundary before this component is decomposed into buildable slices. [DEC-0065] [DEC-0066] [DEC-0095]

## Authority boundary

May, after the fenced reconciliation and contract wiring are ratified: express versioned Book and BMS risk semantics; consume exact QMF values and source observations; represent lineage and registration evidence; evaluate only the reusable risk rules assigned to QMF; and reserve Book-level mode and journal-evidence shapes. CT-22 through CT-25 have no active caller or consumer. [DEC-0039] [DEC-0065] [DEC-0066]

May never: implement trading-entry logic; run a trading-node loop; connect to a venue; write a physical store; promote an artifact into live money without a human; invent Bot/confluence cardinality or exit ownership; treat the recovered Scalping Book as universal; revive the dead parallel-Bot paper-twin design; or revive the dead FORM-0006, DPR, PRS, auctions, or legacy slot machinery. [DEC-0040] [DEC-0041] [DEC-0067] [DEC-0069] [DEC-0077] [DEC-0079] [DEC-0080] [DEC-0093]

This provisional spec reserves contracts only. It grants no permission to implement risk decisions, authorize orders, transition accounts, connect to live money, or infer answers from recommendations.

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Exact money, price, and quantity values | in | [CT-01](../contracts/ct-01-money-quantity.yaml) | COMP-QMF-CORE |
| Exact time and trading-calendar values | in | [CT-02](../contracts/ct-02-time-calendar.yaml) | COMP-QMF-CORE |
| Instrument and venue identity | in | [CT-03](../contracts/ct-03-instrument-identity.yaml) | COMP-QMF-CORE |
| Typed refusals | out | [CT-04](../contracts/ct-04-typed-refusal.yaml) | COMP-QMF-CORE |
| Version, fingerprint, and compatibility values | in/out | [CT-05](../contracts/ct-05-version-fingerprint.yaml) | COMP-QMF-CORE |
| Registry registration | out | [CT-06](../contracts/ct-06-registration.yaml) | COMP-QMF-REGISTRY |
| Lineage edges | out | [CT-07](../contracts/ct-07-lineage-edge.yaml) | COMP-QMF-REGISTRY |
| Source observations | in | [CT-10](../contracts/ct-10-source-observation.yaml) | COMP-QMF-DATA |
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

`GAP(GAP-0018): Resolve Bot-to-confluence cardinality and the one-Book binding schema; DEC-0040 remains a conflict.`

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
| Monetary representation and rounding | `registry:monetary_representation`, `registry:money_rounding_mode` | Null until GAP-0007 resolves exact arithmetic. |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A caller requests risk evaluation through CT-22 or CT-23. | No caller or consumer is wired, so no risk decision or authorization may be produced. `GAP(GAP-0039): Complete the fenced reconciliation and assign the contract wiring first.` | DEC-0065, DEC-0066 |
| FM-2 | A request depends on unresolved exit ownership. | No exit policy may be inferred or routed. `GAP(GAP-0040): Resolve DEC-0067 before implementation.` | DEC-0067 |
| FM-3 | A formula or payload uses dead FORM-0006, DPR, PRS, auctions, or legacy capital slots. | The input is inadmissible and cannot enter CT-23. `GAP(GAP-0011): Define the typed refusal code.` | DEC-0077, DEC-0079, DEC-0093 |
| FM-4 | A proposed paper transition would revive the dead parallel-Bot paper-twin design cited by DEC-0069. | No transition implementation exists: CT-24 remains evidence-only until operator confirmation and GAP-0041 defines states, triggers, duplicate prevention, continuity, rollback, and evidence. | DEC-0069, DEC-0070 |
| FM-5 | A promotion or live-mode transition lacks human authorization. | The component must not promote or activate the artifact. `GAP(GAP-0019): Define the signed evidence.` | DEC-0041 |
| FM-6 | SQS, news, stop-out, alpha-decay, or priority inputs are missing, stale, or ambiguous. | No formula or transition may be invented. The governing GAP-0042 through GAP-0046 marker remains the behavior boundary. | DEC-0072, DEC-0074, DEC-0092, DEC-0094 |
| FM-7 | An implementation assumes CT-25 already hands evidence to qmf-data. | The assumption is invalid: CT-25 is reserved and unwired, and the component must not write a physical store directly. `GAP(GAP-0025): Define the consumer, persistence handoff, and safe failure rule.` | DEC-0048, DEC-0065 |
| FM-8 | One Book is assigned several BMS policies without a ratified multiplicity rule. | The component must not select or merge them. `GAP(GAP-0039): Resolve DEC-0095.` | DEC-0095 |

## Related

Decisions: DEC-0039, DEC-0040, DEC-0041, DEC-0048, DEC-0065, DEC-0066, DEC-0067, DEC-0068, DEC-0070, DEC-0072, DEC-0074, DEC-0076, DEC-0078, DEC-0080, DEC-0092, DEC-0094, DEC-0095. Dead decisions: DEC-0069, DEC-0077, DEC-0079, DEC-0093. Scenarios: [SCN-0005 uncertain venue submission](../scenarios/SCN-0005-uncertain-venue-submission.md), [SCN-0006 Book paper transition](../scenarios/SCN-0006-book-paper-transition.md), [SCN-0007 human promotion](../scenarios/SCN-0007-human-promotion.md), [SCN-0008 pair-scoped news](../scenarios/SCN-0008-pair-scoped-news.md), [SCN-0010 risk conflicts](../scenarios/SCN-0010-risk-boundary-conflicts.md). Knowledge: none drafted.
