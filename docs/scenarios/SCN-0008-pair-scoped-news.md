---
id: SCN-0008
title: News Control Is Pair-Scoped but Has No Live Window
type: scenario
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA]
decisions: [DEC-0065, DEC-0068, DEC-0072, DEC-0119]
sources: [docs/components/qmf-risk.md, docs/registry/variables.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-23-risk-evaluation.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0008: News Control Is Pair-Scoped but Has No Live Window

This scenario preserves the pair-scoped control while refusing to turn a tentative window into a trading rule. The news-calendar source side is now ratified — the news-calendar recorder keeps provider-native identity and revisions through idempotent (source, source-native id, revision) intake, with scheduling outside QMF — but the pair-scoped control's windows, severity, mapping, open-position behavior, and overrides remain unratified. Execution status: **blocked specification; news-calendar source contract ratified**. [DEC-0072] [DEC-0119]

## Given

A governed news-calendar observation may affect one currency represented in an Instrument. The news-calendar recorder (renamed apart from the market-hours calendar and the day-boundary calendar) keeps provider-native identity and revisions, admitted through the ratified idempotent (source, source-native id, revision) intake; corrections are appended, never overwritten; the legal archiving posture remains an open operator item. `registry:news_blackout_before` and `registry:news_blackout_after` are null; event severity, currency mapping, open-position behavior, override authority, and stale-data behavior are not defined. [DEC-0072] [DEC-0119]

`GAP(GAP-0042): Ratify windows, severity, mapping, open-position behavior, and overrides (risk sitting).`

## When

A caller asks whether the Book may act around that event.

## Then

QMF must not apply a global market blackout, copy the tentative window into configuration, or invent allow/deny behavior. A future rule must evaluate only the affected pair and must make unavailable or stale evidence explicit through the typed-refusal vocabulary. The news-calendar recorder's provider-native identity and revision handling are settled (DEC-0119); the control window is not. [DEC-0065] [DEC-0068] [DEC-0072]

## Worked numbers

No before/after duration is authorized. The executable fixture must reference `registry:news_blackout_before` and `registry:news_blackout_after` after GAP-0042 is answered. The recorder's intake key (source, source-native id, revision) is ratified per DEC-0119.
