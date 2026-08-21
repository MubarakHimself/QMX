---
id: KNOW-TRACEABILITY-QMF-V1
title: QMF V1 Decision, Gap, and Feature Traceability
type: knowledge
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMB, COMP-QML]
decisions: [DEC-0001, DEC-0003, DEC-0004, DEC-0024, DEC-0120, DEC-0121, DEC-0124, DEC-0125, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0130, DEC-0131, DEC-0132, DEC-0133, DEC-0134, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0140, DEC-0141, DEC-0142, DEC-0143, DEC-0144, DEC-0145, DEC-0146, DEC-0147, DEC-0148, DEC-0149, DEC-0150, DEC-0151, DEC-0152, DEC-0153, DEC-0154, DEC-0155, DEC-0156, DEC-0157, DEC-0158, DEC-0159, DEC-0160, DEC-0161, DEC-0162, DEC-0163, DEC-0164, DEC-0165, DEC-0166, DEC-0167, DEC-0168, DEC-0169, DEC-0170, DEC-0171, DEC-0172, DEC-0173, DEC-0174, DEC-0175, DEC-0176, DEC-0177, DEC-0178, DEC-0179, DEC-0180, DEC-0181, DEC-0182, DEC-0183, DEC-0184, DEC-0185]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _docwork/feature_inventory.yaml, _docwork/manifest.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md, docs/decisions/ADR-0017-qmb-experimentation-library.md, docs/decisions/ADR-0018-qml-bot-authoring-library.md, docs/architecture/dependencies.yaml, docs/]
generated: 2026-08-18
verified: 2026-08-21
stale_after: 30d
---

# QMF V1 Decision, Gap, and Feature Traceability

This docs-local locator covers every ledger decision (`DEC-0001` through `DEC-0185`), gap (`GAP-0001` through `GAP-0049`), and inventory feature (`FEAT-0001` through `FEAT-0030`). Statuses are copied from the provisional ledger, gap catalog, and feature inventory; a locator is not ratification or implementation permission. The 2026-08-19/20 foundation architecture sitting ratified `DEC-0099` through `DEC-0125` (AD-1 through AD-21 plus dependency, deferral, and scope rulings) and answered `GAP-0001` through `GAP-0015` and `GAP-0018` through `GAP-0030`; `GAP-0016`/`GAP-0017` are deferred to the backtesting sitting. The 2026-08-20 indicators/structure increment ratified `DEC-0126` through `DEC-0134` (AD-22 through AD-25 plus the increment-gate amendments and the school-neutral and escape-hatch laws) and answered `GAP-0031` through `GAP-0034`. The 2026-08-20 venue sitting ratified `DEC-0135` through `DEC-0142` (AD-26 through AD-28, the cTrader venue facts, the broker-identity ruling, two increment-gate amendment records, and the node-material boundary) and answered `GAP-0035` through `GAP-0038`. The 2026-08-20 risk sitting ratified `DEC-0143` through `DEC-0158` (AD-29 through AD-41, the cross-AD amendments to AD-7/10/12/16/17/18/21/24/27/28, and the corpus-precedence and configurable-means-UI standing laws) and answered `GAP-0039` through `GAP-0046`. The 2026-08-20/21 **QMB increment** ratified `DEC-0159` through `DEC-0169` (the QMB child spine B-1 through B-15 plus the click/optuna stack pins and full adoption by delegation) and folded `COMP-QMB` — the experimentation/backtesting library and `qmb` CLI, an application-layer product built ON QMF (ADR-0017, `FEAT-0029`); it partially closed `GAP-0048` (seams ruled), delivered look-ahead prevention for the deferred `GAP-0016`/`GAP-0017`, and advanced `GAP-0049` without closing it. The 2026-08-21 **QML increment** ratified `DEC-0171` through `DEC-0184` (the QML child spine QL-1 through QL-10 at `architecture-QML-2026-08-21/`, status FINAL, run autonomously by operator delegation with a 5-lens reviewer gate applied) and folded `COMP-QML` — the bot-authoring application-layer library built ON QMF (ADR-0018, `FEAT-0030`) — answering `GAP-0047`, with the 2026-08-21 operator veto round then confirming all six delegation-made calls kept and recording two expansion riders as `DEC-0185`; 45 gaps answered, 0 open in total, with `GAP-0016`/`GAP-0017` (registration gate, DEC-0121), `GAP-0048` content, and `GAP-0049` still deferred. Recommendations remain non-authorizing evidence, and no row grants credential, external-connection, order, promotion, live-money, restore, deletion, or destructive authority. [DEC-0001] [DEC-0003] [DEC-0004]

## Decision locator — 185 entries

The locator names the primary docs-local document and section. `dead`, `superseded`, `conflict`, `open`, and `out-of-scope` statuses are preserved so later agents do not revive or silently settle them. Decisions `DEC-0099` through `DEC-0125` were ratified at the foundation architecture sitting; their authoritative source is the ratified [architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), and their absorbed content lands in the lens, component, and contract docs cited below.

| Decision | Status | Primary document and section |
|---|---|---|
| DEC-0001 | `provisional` | [ADR-0001](../decisions/ADR-0001-authority-and-document-first.md), Decision |
| DEC-0002 | `provisional` | [ADR-0001](../decisions/ADR-0001-authority-and-document-first.md), Decision |
| DEC-0003 | `provisional` | [ADR-0001](../decisions/ADR-0001-authority-and-document-first.md), Decision |
| DEC-0004 | `provisional` | [ADR-0001](../decisions/ADR-0001-authority-and-document-first.md), Decision |
| DEC-0005 | `provisional` | [Operations runbook](../lenses/ops/runbook.md), Permission boundary |
| DEC-0006 | `provisional` | [Constitution](../constitution.md), Laws |
| DEC-0007 | `provisional` | [Constitution](../constitution.md), Laws |
| DEC-0008 | `provisional` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0009 | `provisional` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0010 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0011 | `provisional` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0012 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0013 | `provisional` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0014 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0015 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0016 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0017 | `provisional` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0018 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0019 | `provisional` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0020 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0021 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0022 | `provisional` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0023 | `dead` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Options considered |
| DEC-0024 | `provisional` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0025 | `provisional` | [SCN-0001](../scenarios/SCN-0001-core-freeze-gate.md), Core freeze gate |
| DEC-0026 | `provisional` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0027 | `provisional` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0028 | `provisional` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0029 | `provisional` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0030 | `provisional` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0031 | `provisional` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0032 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), freeze-choice status (superseded by DEC-0124) |
| DEC-0033 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0034 | `dead` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Options considered |
| DEC-0035 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0036 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-16 (superseded by DEC-0114) |
| DEC-0037 | `dead` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Options considered |
| DEC-0038 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0039 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0040 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-17 (superseded by DEC-0115) |
| DEC-0041 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0042 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0043 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-19 (superseded by DEC-0117) |
| DEC-0044 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0045 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0046 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0047 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-19 (superseded by DEC-0117) |
| DEC-0048 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0049 | `open` | [Gap report](../gap-report.md), Open ledger decisions |
| DEC-0050 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0051 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0052 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0053 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0054 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0055 | `provisional` | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md), Decision |
| DEC-0056 | `superseded` | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md), superseded by DEC-0128 |
| DEC-0057 | `out-of-scope` | [Gap report](../gap-report.md), Out-of-scope topics |
| DEC-0058 | `provisional` | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md), Decision |
| DEC-0059 | `provisional` | [ADR-0007](../decisions/ADR-0007-venue-neutral-integration.md), Decision |
| DEC-0060 | `provisional` | [ADR-0007](../decisions/ADR-0007-venue-neutral-integration.md), Decision |
| DEC-0061 | `provisional` | [ADR-0007](../decisions/ADR-0007-venue-neutral-integration.md), Decision |
| DEC-0062 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0063 | `dead` | [QMF Venue](../components/qmf-venue.md), Authority boundary |
| DEC-0064 | `out-of-scope` | [QMF Venue](../components/qmf-venue.md), Authority boundary |
| DEC-0065 | `provisional` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
| DEC-0066 | `provisional` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
| DEC-0067 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0147, AD-33) |
| DEC-0068 | `provisional` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
| DEC-0069 | `dead` | [ADR-0009](../decisions/ADR-0009-book-level-paper-mode.md), Options considered |
| DEC-0070 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (confirmed and subsumed by DEC-0149, AD-35) |
| DEC-0071 | `dead` | [ADR-0009](../decisions/ADR-0009-book-level-paper-mode.md), Options considered |
| DEC-0072 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0152, AD-38) |
| DEC-0073 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0074 | `provisional` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0075 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0153, AD-39) |
| DEC-0076 | `provisional` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0077 | `dead` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Options considered |
| DEC-0078 | `provisional` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0079 | `dead` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Options considered |
| DEC-0080 | `provisional` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
| DEC-0081 | `out-of-scope` | [Gap report](../gap-report.md), Out-of-scope topics |
| DEC-0082 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0083 | `out-of-scope` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Decision |
| DEC-0084 | `dead` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Options considered |
| DEC-0085 | `dead` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Options considered |
| DEC-0086 | `dead` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Options considered |
| DEC-0087 | `out-of-scope` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Decision |
| DEC-0088 | `out-of-scope` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Decision |
| DEC-0089 | `out-of-scope` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Decision |
| DEC-0090 | `out-of-scope` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Decision |
| DEC-0091 | `out-of-scope` | [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), Decision |
| DEC-0092 | `provisional` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0093 | `dead` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Options considered |
| DEC-0094 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0155, AD-41) |
| DEC-0095 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0143, AD-29) |
| DEC-0096 | `provisional` | [Constitution](../constitution.md), Laws |
| DEC-0097 | `provisional` | [Constitution](../constitution.md), Laws |
| DEC-0098 | `provisional` | [Performance budgets](../lenses/performance/budgets.md), Baselines |

### Architecture spine decisions — DEC-0099 through DEC-0125

These decisions were ratified at the 2026-08-19/20 foundation architecture sitting. `AD-N` is the spine invariant each carries; the authoritative source is the [architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md). The primary document names where the absorbed content lands docs-local.

| Decision | Status | Spine | Primary document |
|---|---|---|---|
| DEC-0099 | `ratified` | AD-1 | [Stack](../architecture/stack.md), runtime matrix; [Operations runbook](../lenses/ops/runbook.md) |
| DEC-0100 | `ratified` | AD-2 | [Dependencies](../architecture/dependencies.yaml); [Operations runbook](../lenses/ops/runbook.md) |
| DEC-0101 | `ratified` | AD-3 | [Test strategy](../lenses/testing/test-strategy.md), quality tiers |
| DEC-0102 | `ratified` | AD-4 | [Test strategy](../lenses/testing/test-strategy.md), quality tiers |
| DEC-0103 | `ratified` | AD-5 | [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| DEC-0104 | `ratified` | AD-6 | [Security model](../lenses/security/security-model.md), dependency and supply-chain trust |
| DEC-0105 | `ratified` | AD-7 | [CT-01](../contracts/ct-01-money-quantity.yaml) |
| DEC-0106 | `ratified` | AD-8 | [CT-02](../contracts/ct-02-time-calendar.yaml) |
| DEC-0107 | `ratified` | AD-9 | [CT-03](../contracts/ct-03-instrument-identity.yaml) |
| DEC-0108 | `ratified` | AD-10 | [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| DEC-0109 | `ratified` | AD-11 | [CT-04](../contracts/ct-04-typed-refusal.yaml) |
| DEC-0110 | `ratified` | AD-12 | [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| DEC-0111 | `ratified` | AD-13 | [Performance budgets](../lenses/performance/budgets.md) |
| DEC-0112 | `ratified` | AD-14 | [Logging spec](../lenses/observability/logging-spec.md); [Metrics and alerts](../lenses/observability/metrics-and-alerts.md) |
| DEC-0113 | `ratified` | AD-15 | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-15 |
| DEC-0114 | `ratified` | AD-16 | [QMF Registry](../components/qmf-registry.md) (supersedes DEC-0036) |
| DEC-0115 | `ratified` | AD-17 | [QMF Registry](../components/qmf-registry.md) (supersedes DEC-0040) |
| DEC-0116 | `ratified` | AD-18 | [QMF Registry](../components/qmf-registry.md) |
| DEC-0117 | `ratified` | AD-19 | [Data layer](../lenses/data/data-layer.md) (supersedes DEC-0043, DEC-0047) |
| DEC-0118 | `ratified` | AD-20 | [Data layer](../lenses/data/data-layer.md); [Operations runbook](../lenses/ops/runbook.md) |
| DEC-0119 | `ratified` | AD-21 | [Data layer](../lenses/data/data-layer.md); [Logging spec](../lenses/observability/logging-spec.md) |
| DEC-0120 | `ratified` | Dependency direction | [Data layer](../lenses/data/data-layer.md); [Dependencies](../architecture/dependencies.yaml) |
| DEC-0121 | `ratified` | Deferral | [Gap report](../gap-report.md), GAP-0016/GAP-0017; [Incident playbook](../lenses/ops/incident-playbook.md) |
| DEC-0122 | `ratified` | Foundation law | [Constitution](../constitution.md), Laws |
| DEC-0123 | `superseded` | Evidence superseded by DEC-0135 | [QMF Venue](../components/qmf-venue.md); [Gap report](../gap-report.md), Superseded baseline chains |
| DEC-0124 | `superseded` | Freeze-choice status | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md) (supersedes DEC-0032; superseded by DEC-0134) |
| DEC-0125 | `ratified` | Input register | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), Deferred |

DEC-0123 is now `superseded` by DEC-0135: the cTrader time-handling research was re-verified and ratified at the 2026-08-20 venue sitting as the venue-facts sheet with corrected evidence grades — the 2013-forum-grade daily-boundary and BID-derived-trendbar claims were demoted and replaced by measure-per-broker adapter obligations — not carried forward as the original forum-grade evidence (DEC-0135). DEC-0113 (concurrency) and DEC-0125 (five-hats input register) are ratified rulings whose downstream detail lands in later sittings; DEC-0124's freeze-choice status is now `superseded` by DEC-0134, which records four of the six qmf-core freeze choices ratified.

### Indicators and structure increment decisions — DEC-0126 through DEC-0134

These decisions were ratified at the 2026-08-20 indicators/structure increment (spine AD-22 through AD-25). `AD-N` is the spine invariant each carries where one applies; the authoritative source is the [architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md) and ledger entries DEC-0126 through DEC-0134. The primary document names where the absorbed content lands docs-local.

| Decision | Status | Spine | Primary document |
|---|---|---|---|
| DEC-0126 | `ratified` | AD-22 | [CT-16](../contracts/ct-16-indicator.yaml); [qmf-indicators](../components/qmf-indicators.md); [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md) |
| DEC-0127 | `ratified` | AD-23 | [CT-16](../contracts/ct-16-indicator.yaml); [qmf-indicators](../components/qmf-indicators.md) |
| DEC-0128 | `ratified` | AD-24 | [qmf-indicators](../components/qmf-indicators.md); [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md) (supersedes DEC-0056) |
| DEC-0129 | `ratified` | AD-25 | [CT-17](../contracts/ct-17-causal-structure.yaml); [qmf-structure](../components/qmf-structure.md); [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md) |
| DEC-0130 | `ratified` | AD-22/23/24 amendments | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md); [qmf-indicators](../components/qmf-indicators.md) |
| DEC-0131 | `ratified` | AD-25 + cross-AD amendments | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md); [qmf-structure](../components/qmf-structure.md) |
| DEC-0132 | `ratified` | School-neutral law | [Constitution](../constitution.md), Laws |
| DEC-0133 | `ratified` | Escape hatch + graduation | [Constitution](../constitution.md), Laws |
| DEC-0134 | `ratified` | Freeze-choice status | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md) (supersedes DEC-0124) |

GAP-0031 through GAP-0034 are answered by DEC-0126 through DEC-0129 respectively; DEC-0128 supersedes DEC-0056 (light/heavy split) and DEC-0134 supersedes DEC-0124 (freeze-choice status), recording four of six qmf-core freeze choices ratified with the backtest fidelity taxonomy (GAP-0048) and the SR* threshold (GAP-0049) still open.

### Venue increment decisions — DEC-0135 through DEC-0142

These decisions were ratified at the 2026-08-20 venue sitting (spine AD-26 through AD-28 plus the cTrader venue facts, the broker-identity ruling, the increment-gate amendments, and the node-material boundary). `AD-N` is the spine invariant each carries where one applies; the authoritative source is the [architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), ledger entries DEC-0135 through DEC-0142, and the ratified cTrader venue-facts sheet at `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-venue-facts.md`. The primary document names where the absorbed content lands docs-local.

| Decision | Status | Spine | Primary document |
|---|---|---|---|
| DEC-0135 | `ratified` | cTrader venue facts | [cTrader](../components/ctrader.md); [QMF Venue](../components/qmf-venue.md) (supersedes DEC-0123) |
| DEC-0136 | `ratified` | AD-26 | [CT-21](../contracts/ct-21-venue-secret-session.yaml); [QMF Venue](../components/qmf-venue.md); [Constitution](../constitution.md), Laws (L34) |
| DEC-0137 | `ratified` | AD-27 | [CT-19](../contracts/ct-19-venue-command.yaml); [CT-20](../contracts/ct-20-venue-event.yaml); [QMF Venue](../components/qmf-venue.md); [Constitution](../constitution.md), Laws (L35) |
| DEC-0138 | `ratified` | AD-28 | [CT-18](../contracts/ct-18-venue-capabilities.yaml); [QMF Venue](../components/qmf-venue.md) |
| DEC-0139 | `ratified` | AD-9 platform-vs-broker | [QMF Venue](../components/qmf-venue.md); [cTrader](../components/ctrader.md); [Gap report](../gap-report.md), GAP-0037 |
| DEC-0140 | `ratified` | Venue gate amendments | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-26/27/28; [QMF Venue](../components/qmf-venue.md) |
| DEC-0141 | `ratified` | Cross-AD amendments | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), Cross-AD; [CT-01](../contracts/ct-01-money-quantity.yaml); [CT-02](../contracts/ct-02-time-calendar.yaml) |
| DEC-0142 | `ratified` | Node-material boundary | `tracker/trading-node-notes.md` (pointer only); [QMF Venue](../components/qmf-venue.md), Authority boundary |

GAP-0035 through GAP-0038 are answered by DEC-0136, DEC-0137, DEC-0135 + DEC-0139, and DEC-0138 respectively; DEC-0135 supersedes DEC-0123 (cTrader time research) with corrected evidence grades — the 2013-forum-grade daily-boundary and BID-derived-trendbar claims were demoted and replaced by measure-per-broker adapter obligations. DEC-0136 and DEC-0137 add constitution laws L34 (secret references, never values) and L35 (the four-outcome venue uncertainty law); DEC-0142 keeps trading-node runtime material out of QMF docs, referenced only through `tracker/trading-node-notes.md`.

### Risk increment decisions — DEC-0143 through DEC-0158

These decisions were ratified at the 2026-08-20 risk sitting (spine AD-29 through AD-41 plus the cross-AD amendments to AD-7/10/12/16/17/18/21/24/27/28 and two standing laws). `AD-N` is the spine invariant each carries where one applies; the authoritative source is the [architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md) and ledger entries DEC-0143 through DEC-0158. The primary document names where the absorbed content lands docs-local.

| Decision | Status | Spine | Primary document |
|---|---|---|---|
| DEC-0143 | `ratified` | AD-29 | [CT-22](../contracts/ct-22-book-charter.yaml); [CT-24](../contracts/ct-24-book-mode.yaml); [CT-28](../contracts/ct-28-book-binding.yaml); [QMF Risk](../components/qmf-risk.md); [Constitution](../constitution.md), Laws (L36) (supersedes DEC-0095) |
| DEC-0144 | `ratified` | AD-30 | [CT-22](../contracts/ct-22-book-charter.yaml); [CT-27](../contracts/ct-27-bms-definition.yaml); [QMF Risk](../components/qmf-risk.md) |
| DEC-0145 | `ratified` | AD-31 | [CT-25](../contracts/ct-25-risk-journal.yaml); [qmf-data](../components/qmf-data.md); [QMF Risk](../components/qmf-risk.md) |
| DEC-0146 | `ratified` | AD-32 | [CT-22](../contracts/ct-22-book-charter.yaml); [CT-27](../contracts/ct-27-bms-definition.yaml); [CT-32](../contracts/ct-32-performance-result.yaml); [QMF Risk](../components/qmf-risk.md) |
| DEC-0147 | `ratified` | AD-33 | [CT-23](../contracts/ct-23-risk-evaluation.yaml); [CT-29](../contracts/ct-29-exit-record.yaml); [QMF Risk](../components/qmf-risk.md); [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md) (supersedes DEC-0067) |
| DEC-0148 | `ratified` | AD-34 | [CT-19](../contracts/ct-19-venue-command.yaml); [QMF Venue](../components/qmf-venue.md); [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md) |
| DEC-0149 | `ratified` | AD-35 | [CT-24](../contracts/ct-24-book-mode.yaml); [CT-28](../contracts/ct-28-book-binding.yaml); [QMF Risk](../components/qmf-risk.md); [ADR-0009](../decisions/ADR-0009-book-level-paper-mode.md) (supersedes DEC-0070) |
| DEC-0150 | `ratified` | AD-36 | [CT-30](../contracts/ct-30-control-action.yaml); [QMF Risk](../components/qmf-risk.md); [Constitution](../constitution.md), Laws (L39) |
| DEC-0151 | `ratified` | AD-37 | [CT-30](../contracts/ct-30-control-action.yaml); [QMF Risk](../components/qmf-risk.md) |
| DEC-0152 | `ratified` | AD-38 | [CT-31](../contracts/ct-31-control-window.yaml); [QMF Risk](../components/qmf-risk.md); [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md) (supersedes DEC-0072) |
| DEC-0153 | `ratified` | AD-39 | [CT-23](../contracts/ct-23-risk-evaluation.yaml); [CT-16](../contracts/ct-16-indicator.yaml); [QMF Risk](../components/qmf-risk.md); [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md) (supersedes DEC-0075) |
| DEC-0154 | `ratified` | AD-40 | [CT-01](../contracts/ct-01-money-quantity.yaml); [CT-22](../contracts/ct-22-book-charter.yaml); [CT-23](../contracts/ct-23-risk-evaluation.yaml); [QMF Risk](../components/qmf-risk.md); [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md) |
| DEC-0155 | `ratified` | AD-41 | [CT-29](../contracts/ct-29-exit-record.yaml); [CT-32](../contracts/ct-32-performance-result.yaml); [QMF Risk](../components/qmf-risk.md); [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md) (supersedes DEC-0094) |
| DEC-0156 | `ratified` | Corpus-precedence law | [Constitution](../constitution.md), Laws (L37) |
| DEC-0157 | `ratified` | Configurable-means-UI law | [Constitution](../constitution.md), Laws (L38) |
| DEC-0158 | `ratified` | Cross-AD amendments (AD-7/10/12/16/17/18/21/24/27/28) | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), Cross-AD; [CT-01](../contracts/ct-01-money-quantity.yaml); [CT-05](../contracts/ct-05-version-fingerprint.yaml); [CT-18](../contracts/ct-18-venue-capabilities.yaml); [CT-19](../contracts/ct-19-venue-command.yaml) |

GAP-0039 through GAP-0046 are answered by DEC-0143..DEC-0146 (AD-29..32), DEC-0147 + DEC-0148 (AD-33/34), DEC-0149 (AD-35), DEC-0152 (AD-38), DEC-0153 (AD-39), DEC-0154 (AD-40), DEC-0155 (AD-41), and DEC-0150 + DEC-0151 (AD-36/37) respectively. The risk sitting supersedes five earlier entries — DEC-0095 by DEC-0143, DEC-0067 by DEC-0147, DEC-0070 (confirmed and subsumed) by DEC-0149, DEC-0072 by DEC-0152, DEC-0075 by DEC-0153, and DEC-0094 by DEC-0155 — and mints four constitution laws: L36 authority order `bot → book → BMS → operator` (DEC-0143), L37 corpus precedence for risk sources (DEC-0156), L38 configurable-means-UI-editable (DEC-0157), and L39 the exit-preservation invariant (DEC-0150). DEC-0158 records the reviewer-gate cross-AD amendments applied with AD ids stable, including the risk record kinds minted onto AD-16 (CT-22, CT-24, CT-27 through CT-32, and the instrument currency-exposure metadata record) and the `continues-as` edge split into `continues-performance` and `carries-ledger`.

### QMB increment decisions — DEC-0159 through DEC-0169

These decisions were ratified at the 2026-08-20/21 QMB child architecture sitting (spine B-1 through B-15, `architecture-QMB-2026-08-20/`, status FINAL, ratified by operator delegation). `B-N` is the QMB spine invariant each carries where one applies; QMF spine AD-1 through AD-41 binds read-only as the parent. The authoritative source is the [QMB architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md) (`SRC-07`) grounded on the 2026-08-20 backtesting-direction transcript `archive/qmf-7.txt` (`SRC-08`), and ledger entries DEC-0159 through DEC-0169. The primary document names where the absorbed content lands docs-local. QMB is an application-layer product built ON QMF — never a QMF roster package — so these decisions add no QMF package edge and reverse no dependency direction.

| Decision | Status | Spine | Primary document |
|---|---|---|---|
| DEC-0159 | `ratified` | B-1 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [Glossary](../glossary.md) (QMB, `qmb` CLI, doors, as-of set) |
| DEC-0160 | `ratified` | B-3 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [CT-22](../contracts/ct-22-book-charter.yaml), [CT-27](../contracts/ct-27-bms-definition.yaml) (config-fragment lineage) |
| DEC-0161 | `ratified` | B-4/B-5 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md) (pure run, impure orchestrator, governor) |
| DEC-0162 | `ratified` | B-4 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [CT-32](../contracts/ct-32-performance-result.yaml) (read-time per-requirement verdict fold) |
| DEC-0163 | `ratified` | B-10 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [CT-32](../contracts/ct-32-performance-result.yaml), [CT-13](../contracts/ct-13-journal.yaml), [CT-11](../contracts/ct-11-evidence-persistence.yaml) (adoption-not-reinvention) |
| DEC-0164 | `ratified` | B-6/B-7 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [Gap report](../gap-report.md), GAP-0048 (fidelity seams, optimistic taint, calibration) |
| DEC-0165 | `ratified` | B-15 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [variables registry](../registry/variables.yaml) (`qmb_stale_evidence_severity`) |
| DEC-0166 | `ratified` | B-11 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [Dukascopy](../components/dukascopy.md); [Gap report](../gap-report.md), Dukascopy licensing flag (resolved by DEC-0170) |
| DEC-0170 | `ratified` | Licensing posture | [Dukascopy](../components/dukascopy.md); [QMB](../components/qmb.md); [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md) — personal-use ruling closes the DEC-0166 ops flag; license-tag mechanism unchanged |
| DEC-0167 | `ratified` | B-13 | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [Stack](../architecture/stack.md) (distribution channel) |
| DEC-0168 | `ratified` | Stack pins | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [variables registry](../registry/variables.yaml) (`qmb_cli_pin`, `qmb_sampler_pin`) |
| DEC-0169 | `ratified` | B-1..B-15 adoption | [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md); [Gap report](../gap-report.md), GAP-0016/0017/0047/0048/0049 |

DEC-0159 realizes the glossary's reserved "future backtesting library" slot as `COMP-QMB` and settles the experimentation/backtest vocabulary (`FEAT-0029`, the implementing feature). DEC-0163 amends three ratified contracts as declared adoption notes and extensions: CT-32 gains chart-series and trade-event-reference extensions and QMB as an intended **producer**, CT-13 gains the replay-world run-loop emission note, and CT-11 restates that per-run logs are AD-14 operational only and never evidence. DEC-0161 mints the governor and per-run-limit registry rows (`qmb_governor_cpu_budget`, `qmb_governor_memory_budget`, `qmb_run_time_limit`, `qmb_run_memory_limit`) and DEC-0165 the `qmb_stale_evidence_severity` row — all configurable UI-editable per L38/DEC-0157 — while DEC-0168 mints the two non-configurable exact stack pins (`qmb_cli_pin`, `qmb_sampler_pin`). GAP-0048 is partially closed by DEC-0164 (seams) with DEC-0161/DEC-0169 answering its sandbox and matrix halves; GAP-0016/GAP-0017 gain look-ahead prevention through DEC-0169 (spine B-2/B-8/B-12) while their registration gate and counting policy stay deferred per DEC-0121; GAP-0049 advances without closing, and GAP-0047 — advanced here — is subsequently answered by the 2026-08-21 QML increment (DEC-0171 through DEC-0184, ADR-0018). DEC-0166 leaves the Dukascopy data-licensing question an open ops item flagged to the operator, gating governed evidence only.

### QML increment decisions — DEC-0171 through DEC-0185

These decisions were ratified at the 2026-08-21 QML child architecture sitting (spine QL-1 through QL-10, `architecture-QML-2026-08-21/`, status FINAL, run autonomously by operator delegation with every without-operator call tagged in the memlog and individually overturnable; reviewer gate applied at desk — 5 lenses, 34 findings, all applied). `QL-N` is the QML spine invariant each carries where one applies; QMF spine AD-1 through AD-41 binds read-only as the parent. The authoritative source is the [QML architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md) (`SRC-09`) grounded on the 2026-08-21 QML sitting transcript `archive/qml.txt` (`SRC-10`), and ledger entries DEC-0171 through DEC-0184, plus the 2026-08-21 operator veto-round closeout DEC-0185 (ratified by operator direct ruling at the DEC-0184 veto checkpoint, not at the sitting). The primary document names where the absorbed content lands docs-local. QML is an application-layer product built ON QMF — never a QMF roster package — so these decisions add no QMF package edge and reverse no dependency direction.

| Decision | Status | Spine | Primary document |
|---|---|---|---|
| DEC-0171 | `ratified` | QL-1 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md) |
| DEC-0172 | `ratified` | QL-2 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-33](../contracts/ct-33-bot-definition.yaml) |
| DEC-0173 | `ratified` | QL-3 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-33](../contracts/ct-33-bot-definition.yaml) |
| DEC-0174 | `ratified` | QL-4 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-33](../contracts/ct-33-bot-definition.yaml); [CT-22](../contracts/ct-22-book-charter.yaml) |
| DEC-0175 | `ratified` | QL-5 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-34](../contracts/ct-34-confluence.yaml) |
| DEC-0176 | `ratified` | QL-6 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-06](../contracts/ct-06-registration.yaml); [CT-22](../contracts/ct-22-book-charter.yaml) |
| DEC-0177 | `ratified` | QL-7 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-23](../contracts/ct-23-risk-evaluation.yaml) |
| DEC-0178 | `ratified` | QL-8 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-22](../contracts/ct-22-book-charter.yaml); [CT-06](../contracts/ct-06-registration.yaml) |
| DEC-0179 | `ratified` | QL-9 | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-29](../contracts/ct-29-exit-record.yaml); [CT-23](../contracts/ct-23-risk-evaluation.yaml) |
| DEC-0180 | `ratified` | QL-10 + QL-1 versioning | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [Stack](../architecture/stack.md) |
| DEC-0181 | `ratified` | CT-22 format mint (parent) | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-22](../contracts/ct-22-book-charter.yaml); [QMF Risk](../components/qmf-risk.md) |
| DEC-0182 | `ratified` | CT-23 format mint (parent) | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-23](../contracts/ct-23-risk-evaluation.yaml); [QMF Risk](../components/qmf-risk.md) |
| DEC-0183 | `ratified` | QMB sibling coordination | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [QMB](../components/qmb.md) |
| DEC-0184 | `ratified` | Spine adoption umbrella | [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [Gap report](../gap-report.md); [Glossary](../glossary.md); [Constitution](../constitution.md), Laws (L30 scope annotation) |
| DEC-0185 | `ratified` | Veto round | [Changelog](../changelog.md), 2026-08-21 QML entry; [QML](../components/qml.md); [CT-34](../contracts/ct-34-confluence.yaml); [CT-22](../contracts/ct-22-book-charter.yaml) |

DEC-0171 realizes the glossary's reserved QML slot as `COMP-QML` — the bot-authoring application-layer library built ON QMF, never a roster package — settled by `FEAT-0030`, the implementing feature. DEC-0173 fills AD-16's reserved Bot kind and DEC-0175 mints the confluence kind as qmf-registry per-kind contracts (CT-33, CT-34) authored via the QML library, while DEC-0176 adds the strategy family as a dated AD-9 metadata record kind under CT-06's addable-kinds law with no new CT number — so CT-06 gains the Bot-kind-body ruling and the strategy-family addable kind. DEC-0181 and DEC-0182 carry the CT-22 v2 and CT-23 v2 AD-5 format mints (owned by `COMP-QMF-RISK`, QML-authored semantics, mandatory migration notes; format-1 artifacts stay readable forever). No `variables.yaml` rows are minted — QML mints no values or pins. GAP-0047 is answered/closed by the spine adoption (DEC-0184); GAP-0016/GAP-0017 (registration gate, DEC-0121), GAP-0048 content, and GAP-0049 stay deferred. The 2026-08-21 operator veto round (DEC-0185) reviewed the six delegation-made calls, confirmed all of them kept, and recorded two expansion riders — a confluence leg may carry both a producer binding and a child-confluence cite (CT-34), and a Book's per-family `ExitLogicRef` may declare an adopt-the-bot's-advisory-stop mode so bot-owned exit methodologies are first-class (CT-22) — plus the no-second-CLI ruling; it is ratified by operator direct ruling at the DEC-0184 veto checkpoint, not at the sitting.

## Gap locator — 49 entries

Every row links the full [gap report](../gap-report.md) and the most direct architecture, component, or contract boundary. The foundation architecture sitting `answered` GAP-0001 through GAP-0015 and GAP-0018 through GAP-0030 (answering DEC named per row) and `deferred` GAP-0016/GAP-0017 to the backtesting sitting; the 2026-08-20 indicators/structure increment `answered` GAP-0031 through GAP-0034 (DEC-0126 through DEC-0129); the 2026-08-20 venue sitting `answered` GAP-0035 through GAP-0038 (DEC-0136, DEC-0137, DEC-0135 + DEC-0139, DEC-0138); the 2026-08-20 risk sitting `answered` GAP-0039 through GAP-0046 (DEC-0143 through DEC-0155). The 2026-08-20/21 QMB increment (DEC-0159 through DEC-0169) partially closed GAP-0048 (fidelity seams ruled, DEC-0164), delivered look-ahead prevention for the deferred GAP-0016/GAP-0017 (spine B-2/B-8/B-12, DEC-0169), and advanced GAP-0049 without closing it. The 2026-08-21 QML increment (DEC-0171 through DEC-0184, child spine QL-1 through QL-10 at `architecture-QML-2026-08-21/`, run autonomously by operator delegation with a 5-lens reviewer gate applied) folded `COMP-QML` — the bot-authoring application-layer library built ON QMF (ADR-0018, `FEAT-0030`) — and `answered` GAP-0047. In total 45 gaps are answered and 0 remain open, with GAP-0016/GAP-0017 (registration gate, DEC-0121), GAP-0048 content, and GAP-0049 deferred. An `answered` row is answered at the ruling level while per-field schema detail may still be documentation-time work; the newly-answered risk gaps now carry `blocking: false` in the catalog, matching the ratified contract surface. GAP-0048 and GAP-0049 name `COMP-QMB` among their consumers in the catalog.

| Gap | Status | Blocking | Primary boundary |
|---|---|---:|---|
| GAP-0001 | `answered` | `true` | Answered by DEC-0099 (AD-1); [stack](../architecture/stack.md), runtime matrix |
| GAP-0002 | `answered` | `true` | Answered by DEC-0100 (AD-2); [dependencies](../architecture/dependencies.yaml), component packaging |
| GAP-0003 | `answered` | `true` | Answered by DEC-0101 (AD-3); [test strategy](../lenses/testing/test-strategy.md) |
| GAP-0004 | `answered` | `true` | Answered by DEC-0102 (AD-4); [test strategy](../lenses/testing/test-strategy.md), quality tiers |
| GAP-0005 | `answered` | `true` | Answered by DEC-0103 (AD-5); [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| GAP-0006 | `answered` | `true` | Answered by DEC-0104 (AD-6); [security model](../lenses/security/security-model.md), dependency trust |
| GAP-0007 | `answered` | `true` | Answered by DEC-0105 (AD-7); [CT-01](../contracts/ct-01-money-quantity.yaml) |
| GAP-0008 | `answered` | `true` | Answered by DEC-0106 (AD-8); [CT-02](../contracts/ct-02-time-calendar.yaml) |
| GAP-0009 | `answered` | `true` | Answered by DEC-0107 (AD-9); [CT-03](../contracts/ct-03-instrument-identity.yaml) |
| GAP-0010 | `answered` | `true` | Answered by DEC-0108 (AD-10); [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| GAP-0011 | `answered` | `true` | Answered by DEC-0109 (AD-11); [CT-04](../contracts/ct-04-typed-refusal.yaml) |
| GAP-0012 | `answered` | `true` | Answered by DEC-0110 (AD-12); [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| GAP-0013 | `answered` | `true` | Answered by DEC-0111 (AD-13); [performance budgets](../lenses/performance/budgets.md). Method ratified; numeric budgets await baselines. |
| GAP-0014 | `answered` | `true` | Answered by DEC-0114 (AD-16); [CT-06](../contracts/ct-06-registration.yaml) |
| GAP-0015 | `answered` | `true` | Answered by DEC-0114 (AD-16); [CT-07](../contracts/ct-07-lineage-edge.yaml) |
| GAP-0016 | `deferred` | `false` | Deferred by DEC-0121 to the backtesting sitting; [CT-08](../contracts/ct-08-gate-evidence.yaml). Bitemporal ingredients ratified; look-ahead **prevention** delivered by QMB (spine B-2/B-8/B-12, DEC-0169), only the registration gate stays deferred. |
| GAP-0017 | `deferred` | `false` | Deferred by DEC-0121 to the backtesting sitting; [CT-08](../contracts/ct-08-gate-evidence.yaml). QMB makes every trial/replicate/walk-forward window a ledgered run (DEC-0161, DEC-0169), so the counter's raw material is complete; the counting policy stays deferred. |
| GAP-0018 | `answered` | `true` | Answered by DEC-0115 (AD-17); [CT-22](../contracts/ct-22-book-charter.yaml). Multiplicity ratified; the full Bot schema is now ruled via CT-33 (DEC-0173). |
| GAP-0019 | `answered` | `true` | Answered by DEC-0116 (AD-18) as a skeleton; [CT-06](../contracts/ct-06-registration.yaml). Evidence checklist accretes later. |
| GAP-0020 | `answered` | `true` | Answered by DEC-0117 (AD-19); [qmf-data](../components/qmf-data.md); [data layer](../lenses/data/data-layer.md), seven room-roles |
| GAP-0021 | `answered` | `true` | Answered by DEC-0117 (AD-19); [CT-09](../contracts/ct-09-registry-persistence.yaml); [data layer](../lenses/data/data-layer.md), store stack |
| GAP-0022 | `answered` | `true` | Answered by DEC-0118 (AD-20); [qmf-data store](../components/qmf-data-store.md) |
| GAP-0023 | `answered` | `true` | Answered by DEC-0117 (AD-19); [CT-10](../contracts/ct-10-source-observation.yaml) |
| GAP-0024 | `answered` | `true` | Answered by DEC-0119 (AD-21); [CT-12](../contracts/ct-12-dataset-split.yaml). Seal enforced now. |
| GAP-0025 | `answered` | `true` | Answered by DEC-0119 (AD-21); [CT-13](../contracts/ct-13-journal.yaml) |
| GAP-0026 | `answered` | `true` | Answered by DEC-0118 (AD-20); [CT-11](../contracts/ct-11-evidence-persistence.yaml) |
| GAP-0027 | `answered` | `true` | Answered by DEC-0118 (AD-20); [CT-14](../contracts/ct-14-backup-restore.yaml). Numeric objectives at node/ops. |
| GAP-0028 | `answered` | `true` | Answered by DEC-0119 (AD-21); [data ingest](../components/qmf-data-ingest.md), authority boundary |
| GAP-0029 | `answered` | `true` | Answered by DEC-0119 (AD-21); [CT-15](../contracts/ct-15-external-source-adapter.yaml). Legal archiving posture stays an open operator item. |
| GAP-0030 | `answered` | `true` | Answered by DEC-0119 (AD-21); [CT-10](../contracts/ct-10-source-observation.yaml). Symbol/depth specifics ratified under DEC-0135/DEC-0138. |
| GAP-0031 | `answered` | `true` | Answered by DEC-0126 (AD-22); [CT-16](../contracts/ct-16-indicator.yaml); [qmf-indicators](../components/qmf-indicators.md). Two-mode protocol and series vocabulary/BarSpec ratified; per-field schema at documentation time. |
| GAP-0032 | `answered` | `true` | Answered by DEC-0127 (AD-23); [CT-16](../contracts/ct-16-indicator.yaml). TA-Lib 0.7.1 canonical-arithmetic pin ratified. |
| GAP-0033 | `answered` | `false` | Answered by DEC-0128 (AD-24, supersedes DEC-0056); [CT-16](../contracts/ct-16-indicator.yaml). Light/heavy four-bound rule ratified. |
| GAP-0034 | `answered` | `true` | Answered by DEC-0129 (AD-25); [CT-17](../contracts/ct-17-causal-structure.yaml); [qmf-structure](../components/qmf-structure.md). Causal structure lifecycle ratified. |
| GAP-0035 | `answered` | `true` | Answered by DEC-0136 (AD-26); [CT-21](../contracts/ct-21-venue-secret-session.yaml). Secret-reference lifecycle ratified — references never values. |
| GAP-0036 | `answered` | `true` | Answered by DEC-0137 (AD-27); [CT-19](../contracts/ct-19-venue-command.yaml) and [CT-20](../contracts/ct-20-venue-event.yaml). Four-outcome uncertainty law and read-time order-state fold ratified. |
| GAP-0037 | `answered` | `true` | Answered by DEC-0135 and DEC-0139; [CT-18](../contracts/ct-18-venue-capabilities.yaml). cTrader venue facts ratified (DEC-0135 supersedes DEC-0123 with corrected evidence grades) and broker identity is deployment configuration (DEC-0139). |
| GAP-0038 | `answered` | `true` | Answered by DEC-0138 (AD-28); [CT-18](../contracts/ct-18-venue-capabilities.yaml). One neutral port of four contracts with the capability-declaration/venue-observation-profile split ratified. |
| GAP-0039 | `answered` | `false` | Answered by DEC-0143..DEC-0146 (AD-29..32); [CT-22](../contracts/ct-22-book-charter.yaml), [CT-24](../contracts/ct-24-book-mode.yaml), [CT-25](../contracts/ct-25-risk-journal.yaml), [CT-27](../contracts/ct-27-bms-definition.yaml), [CT-28](../contracts/ct-28-book-binding.yaml). BMS is account-facing; binding chain and admission ratified. |
| GAP-0040 | `answered` | `false` | Answered by DEC-0147 + DEC-0148 (AD-33/34, resolving DEC-0067); [CT-23](../contracts/ct-23-risk-evaluation.yaml), [CT-29](../contracts/ct-29-exit-record.yaml), [CT-19](../contracts/ct-19-venue-command.yaml). Book owns exit policy; amend_protection minted. |
| GAP-0041 | `answered` | `false` | Answered by DEC-0149 (AD-35, confirming DEC-0070); [CT-24](../contracts/ct-24-book-mode.yaml), [CT-28](../contracts/ct-28-book-binding.yaml). Paper is a Book-level standing evidence state, one active target per live binding. |
| GAP-0042 | `answered` | `false` | Answered by DEC-0152 (AD-38, supersedes DEC-0072); [CT-31](../contracts/ct-31-control-window.yaml). One control-window contract; entries-only block, widths configurable UI-editable. |
| GAP-0043 | `answered` | `false` | Answered by DEC-0153 (AD-39, supersedes DEC-0075); [CT-23](../contracts/ct-23-risk-evaluation.yaml), [CT-16](../contracts/ct-16-indicator.yaml). Ratio SQS adopted as a CT-16 configured producer, block-only. |
| GAP-0044 | `answered` | `false` | Answered by DEC-0154 (AD-40); [CT-01](../contracts/ct-01-money-quantity.yaml), [CT-22](../contracts/ct-22-book-charter.yaml), [CT-23](../contracts/ct-23-risk-evaluation.yaml). Three R faces, USD numeraire, dimensional law; B split; FORM-0006 the permanent negative test. |
| GAP-0045 | `answered` | `false` | Answered by DEC-0155 (AD-41, supersedes DEC-0094); [CT-29](../contracts/ct-29-exit-record.yaml), [CT-32](../contracts/ct-32-performance-result.yaml). qualifying_loss_exit vs venue_liquidation split; bench fold; evidence primitives only. |
| GAP-0046 | `answered` | `false` | Answered by DEC-0150 + DEC-0151 (AD-36/37); [CT-30](../contracts/ct-30-control-action.yaml). One arbitration point per command stream; kill switch vs kill line named apart. |
| GAP-0047 | `answered` | `false` | Answered by DEC-0171–DEC-0184 (QL-1..QL-10); [Gap report](../gap-report.md); [ADR-0018](../decisions/ADR-0018-qml-bot-authoring-library.md); [QML](../components/qml.md); [CT-33](../contracts/ct-33-bot-definition.yaml), [CT-34](../contracts/ct-34-confluence.yaml). Answered 2026-08-21 by the QML sitting. |
| GAP-0048 | `deferred` *(partially closed)* | `false` | [Gap report](../gap-report.md); [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md). Seams ruled (DEC-0164): ports, partial fills, lowest-wins, optimistic taint, calibration-not-invention; sandbox/matrix halves answered by the QMB architecture (DEC-0161, DEC-0169). Taxonomy values, calibration content, parity contracts, and simulated-time typing still open. |
| GAP-0049 | `deferred` | `false` | [Gap report](../gap-report.md); [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md). Raw material accrues by construction (DEC-0161, DEC-0169) plus B-8 anti-overfit sensitivity per sweep; thresholds, SR*, and the staged funnel stay its sitting. |

## Feature locator — 30 entries

Waves are the derived dependency waves from `_docwork/feature_inventory.yaml`. The blocker summaries preserve the dependency edges but replace stale wording with the current venue contract topology; they do not declare any blocker complete, and the venue contracts being filled at version 1 does not lift the corpus-wide provisional gate or grant implementation authority. `FEAT-0028` (forex market-hours calendar extension) and `FEAT-0029` (QMB experimentation library and `qmb` CLI) join the inventory; `FEAT-0029` is the QMB increment's headline feature and carries its own gate below. `FEAT-0030` (QML bot-authoring library) joins as the QML increment's headline feature, blocked only on the qmf-core, qmf-registry, and qmf-risk contract surfaces it imports — never on `FEAT-0029` or any node feature (DEC-0180).

| Feature | Wave | Component | Status | Blocker summary |
|---|---:|---|---|---|
| FEAT-0001 | 1 | [COMP-QMF-CORE](../components/qmf-core.md) | `planned` | None. |
| FEAT-0002 | 1 | [COMP-QMF-CORE](../components/qmf-core.md) | `planned` | None. |
| FEAT-0003 | 1 | [COMP-QMF-CORE](../components/qmf-core.md) | `planned` | None. |
| FEAT-0004 | 1 | [COMP-QMF-CORE](../components/qmf-core.md) | `planned` | None. |
| FEAT-0005 | 2 | [COMP-QMF-CORE](../components/qmf-core.md) | `planned` | FEAT-0001 through FEAT-0004: core value, time, identity, and refusal contracts. |
| FEAT-0006 | 3 | [COMP-QMF-REGISTRY](../components/qmf-registry.md) | `planned` | FEAT-0005: canonical serialization, fingerprint, and compatibility substrate. |
| FEAT-0007 | 4 | [COMP-QMF-REGISTRY](../components/qmf-registry.md) | `planned` | FEAT-0006: typed registry identities and canonical addresses. |
| FEAT-0008 | 5 | [COMP-QMF-REGISTRY](../components/qmf-registry.md) | `planned` | FEAT-0007: identity and lineage contracts. |
| FEAT-0009 | 6 | [COMP-QMF-REGISTRY](../components/qmf-registry.md) | `planned` | FEAT-0008: causality-gate outcome and refusal evidence. |
| FEAT-0010 | 6 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0008: observation, knowledge-time, identity, and causality evidence. |
| FEAT-0011 | 7 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0010: bitemporal fact identity and knowledge-time contract. |
| FEAT-0012 | 8 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0011: dataset-release and sealed-holdout evidence; CT-13 mutation semantics remain GAP-0025/GAP-0026. |
| FEAT-0013 | 9 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0012: journal boundary plus fact and dataset-release evidence; backup completion and validation remain GAP-0027. |
| FEAT-0014 | 10 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0013: fact, content-integrity, backup-unit, and restore contracts. |
| FEAT-0015 | 11 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0014: persisted fact and backup-safe storage boundary. |
| FEAT-0016 | 12 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0015: sealed-holdout access and override evidence. |
| FEAT-0017 | 13 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0016: settled raw-fact, release, and journal persistence boundaries; cadence, completion, and validation remain GAP-0027. |
| FEAT-0018 | 14 | [COMP-QMF-DATA](../components/qmf-data.md) | `planned` | FEAT-0017: storage and off-machine backup/restore boundaries; no completion or validation rule is assumed. |
| FEAT-0019 | 7 | [COMP-QMF-INDICATORS](../components/qmf-indicators.md) | `planned` | FEAT-0010: canonical bitemporal inputs and derived-evidence identity. |
| FEAT-0020 | 8 | [COMP-QMF-INDICATORS](../components/qmf-indicators.md) | `planned` | FEAT-0019: package-neutral indicator protocol and conformance harness. |
| FEAT-0021 | 7 | [COMP-QMF-STRUCTURE](../components/qmf-structure.md) | `planned` | FEAT-0010: bitemporal fact and causality-claim integration. |
| FEAT-0022 | 8 | [COMP-QMF-STRUCTURE](../components/qmf-structure.md) | `planned` | FEAT-0021: structure protocol, provenance, confirmation, and invalidation contract. |
| FEAT-0023 | 9 | [COMP-QMF-VENUE](../components/qmf-venue.md) | `planned` | FEAT-0012: CT-13 evidence boundary. GAP-0036/GAP-0038 answered (DEC-0137/DEC-0138): CT-18 through CT-21 are filled at format version 1 as ratified contract surface; the caller stays unassigned in QMF by design, so CT-19 caller/authorization evidence remains GAP-0039. |
| FEAT-0024 | 10 | [COMP-QMF-VENUE](../components/qmf-venue.md) | `planned` | FEAT-0023: venue capability and session shapes filled at version 1. GAP-0035/GAP-0037 answered (DEC-0136/DEC-0135/DEC-0139): the AD-26 secret lifecycle and ratified venue facts govern, and broker identity is deployment configuration. |
| FEAT-0025 | 13 | [COMP-QMF-VENUE](../components/qmf-venue.md) | `planned` | FEAT-0024 and FEAT-0016: session plus data-persistence boundaries; market data is homed at CT-10/CT-15 with no fifth contract (DEC-0138), and the daily-boundary and bar-price basis are measured-per-broker verify-or-refuse obligations (DEC-0135). |
| FEAT-0026 | 14 | [COMP-QMF-VENUE](../components/qmf-venue.md) | `planned` | FEAT-0025: session, instrument, time, and evidence boundaries; AD-27 (DEC-0137) supplies the four-outcome command contract with explicit UNKNOWN minting, and the caller/authorization assignment stays with GAP-0039. |
| FEAT-0027 | 10 | [COMP-QMF-RISK](../components/qmf-risk.md) | `planned` | FEAT-0023: ratified venue seam (CT-18 through CT-21). Risk planning is complete: GAP-0039 through GAP-0046 answered (DEC-0143 through DEC-0155), CT-22 through CT-25 filled and CT-27 through CT-32 minted; the feature now covers implementing the ratified contracts, still factory-only. Detailed gate below. |
| FEAT-0028 | 2 | [COMP-QMF-CALENDAR-FOREX](../components/qmf-calendar-forex.md) | `planned` | FEAT-0002: implements the CT-02 calendar-provider protocol (17:00 America/New_York accounting rollover, weekend gaps, in-scope holidays). No open blocking gap — GAP-0008 answered and the rollover is operator-adopted (DEC-0106); on its own SemVer ladder outside the roster lockstep (DEC-0100). |
| FEAT-0029 | 13 | [COMP-QMB](../components/qmb.md) | `planned` | FEAT-0027 (ratified Book/BMS/exit/performance contracts CT-22/23/27/28/29/32), FEAT-0015 (split-governed dataset access and sealed-holdout enforcement), FEAT-0016 (journal persistence for CT-13 run events), FEAT-0020 (CT-16 indicators on closed data), FEAT-0022 (CT-17 causal structure on closed data). QMB is an application-layer product built ON QMF (DEC-0159); it adds no QMF package edge and reverses no dependency direction (DEC-0169). Ratified by operator delegation (spine B-1..B-15 FINAL); runs are world=replay with all fills optimistic-tainted until GAP-0048 (DEC-0164). Detailed gate below. |
| FEAT-0030 | 11 | [COMP-QML](../components/qml.md) | `planned` | FEAT-0005 (qmf-core canonical serialization and fp1 identity substrate), FEAT-0007 (the qmf-registry per-kind identity families, canonical addresses, and lineage edges CT-33/CT-34 and branches-from versioning ride, transitively over FEAT-0006), FEAT-0027 (the qmf-risk CT-22/CT-23/CT-27/CT-28/CT-29 Book/exit/binding/door contracts the CT-22 v2 / CT-23 v2 format mints amend and governed bots resolve exits and cite seats through). QML imports `qmf-core`, `qmf-registry`, and `qmf-risk` only and never `qmf-venue` (DEC-0171); it mints no QMF-ladder contract of its own and reverses no dependency direction. Ratified by operator delegation (spine QL-1..QL-10 FINAL); QML builds before the trading node and may run alongside QMB — it does NOT block on `FEAT-0029` or any node feature, and QMB's conformant-bot adapter half rides FEAT-0029's lane and consumes the CT-33 this feature authors (DEC-0180). GAP-0047 answered 2026-08-21. |

## FEAT-0027 scope and gate

FEAT-0027's fenced discovery is complete at the planning level. The 2026-08-20 risk sitting answered GAP-0039 through GAP-0046 (DEC-0143 through DEC-0155, spine AD-29 through AD-41), filling CT-22 through CT-25 and minting CT-27 through CT-32 at format version 1. The feature now covers implementing those ratified contracts. It still authorizes no Book/BMS runtime, risk decision, exit, order authorization, venue call, account transition, credential use, live-money action, journal handoff, or store write: the contracts are `defined-unwired` surface, and implementation authority arrives only through the factory pipeline.

### Ratified inputs the implementation consumes

- DEC-0040 is `superseded` by DEC-0115: a Bot contains one-or-more confluences, recursively, and re-binding never mints a new Bot. The full Bot/QML schema is now ruled via CT-33 (DEC-0173; GAP-0047 answered 2026-08-21 by the QML sitting); the Book-to-BMS binding chain is ratified (DEC-0143, AD-29).
- DEC-0067 is `superseded` by DEC-0147 (AD-33): the Book owns exit policy for the life of a position and Bots propose risk-monotonic exits through the versioned CT-23 door. The exit-ownership conflict is closed.
- DEC-0069 stays `dead`: parallel Bot paper twins must not be revived. DEC-0070 is confirmed and subsumed by DEC-0149 (AD-35): paper is a Book-level standing evidence state; CT-24 carries the mode and binding-transition surface, no longer evidence-only.
- GAP-0039 through GAP-0046 are answered: Book/BMS schemas and binding chain (DEC-0143, DEC-0144, DEC-0146), journals-as-projections (DEC-0145), exit ownership and amend_protection (DEC-0147, DEC-0148), paper mode (DEC-0149), control actions and same-tick priority (DEC-0150, DEC-0151), protection windows (DEC-0152), SQS V1 (DEC-0153), the R/dimensional law (DEC-0154), and the bench/performance evidence base (DEC-0155).
- R is one relationship with three typed faces frozen at admission (DEC-0154, AD-40); the feature must not restate a registry value as a ratified constant, and must keep dead FORM-0006, DPR, PRS, and legacy capital-slot machinery dead — FORM-0006 is retained only as the dimensional suite's permanent negative test.

### Topology the implementation must preserve

- Downstream QMF components consume CT-10 from `COMP-QMF-DATA`; `COMP-QMF-DATA-INGEST` and `COMP-QMF-VENUE` may produce CT-10 into Data, but downstream components never depend on Data-Ingest.
- The risk contracts add **no** package import edge: `COMP-QMF-RISK` depends only on `COMP-QMF-CORE`. Risk records are qmf-core value types wrapped into registry records by the composition root, and dispatch reaches the venue through qmf-core-defined sink protocols — the risk sitting requests no new edge (DEC-0158).
- CT-22, CT-24, CT-27, CT-28, CT-29, CT-30, CT-31, and CT-32 persist through `COMP-QMF-REGISTRY` and `COMP-QMF-DATA` as intended consumers, wired by the composition root when the factory ships; they carry no active QMF V1 wiring today.
- CT-23 is the bot-to-Book inbound door; its caller is the node/bot layer, node-boundary and unassigned in QMF by design (DEC-0147, DEC-0142). CT-25 declares entity journals as read-time projections over qmf-data's stored streams with the command-fingerprint join pinned (DEC-0145).
- CT-19 gains the fifth command kind amend_protection (DEC-0148, AD-34); the venue command transport stays consumer-blind and the caller node-boundary.

### Entry and exit gate

The inventory edge from FEAT-0023 remains an ordering constraint, not proof that any seam is wired. The foundation, data, registry, venue, and risk blockers are all ratified (GAP-0002 through GAP-0046 with GAP-0016/GAP-0017 deferred; DEC-0099 through DEC-0119, DEC-0135 through DEC-0139, and DEC-0143 through DEC-0155), so FEAT-0027 has no remaining planning blocker. Its exit conditions are now implementation-shaped: the ratified Book/BMS, exit, paper-mode, control, window, SQS, dimensional, and performance contracts must be built through the factory lanes, and dependency plus registry artifacts kept current through the documentation change protocol. Until the factory wires and authorizes it, `COMP-QMF-RISK` remains non-buildable outside that pipeline, all CT-22 through CT-32 handoffs remain inactive, and human-only promotion remains absolute.

## FEAT-0029 scope and gate

FEAT-0029 is the QMB experimentation library and `qmb` CLI — the implementing feature for `COMP-QMB`, ratified at the planning level by the 2026-08-20/21 QMB increment (spine B-1 through B-15 FINAL, ADR-0017, DEC-0159 through DEC-0169). It covers building the ratified spine; it authorizes no run, no order, no credential use, no live-money action, and no promotion. QMB publishes; the Book door and the operator act (DEC-0162).

### Ratified inputs the implementation consumes

- One resolved, read-only, fingerprinted run-config per run, compiled with precedence flags > run spec > BMS fragment > Book fragment > workspace defaults over disjoint Book/BMS key namespaces; fragments are derived fingerprinted artifacts carrying AD-16 lineage to CT-22/CT-27, and every run mints one AD-29 binding with world=replay (DEC-0160).
- A pure `run()` returning a CT-32 performance-result, and one impure orchestrator owning per-run operational logs and exactly one WriterId-scoped JSONL ledger line per run (aborted lines included), with the min(cpu, ram) governor bounding process-per-run parallelism (DEC-0161). The bar verdict is a reader-derived per-requirement read-time fold against the Book bar as resolved at run time, never a stored pass/fail (DEC-0162).
- The result artifact IS CT-32 with chart-series and trade-event-reference declared extensions; run trading events are CT-13 journal events on writer-scoped streams in the run's world; per-run logs are AD-14 operational only, never CT-11 evidence (DEC-0163).
- Fidelity seams — separate fill/slippage/cost ports plus financing as a scheduled position-level event, lowest-fidelity-wins, an optimistic taint on every fill until GAP-0048 rules the taxonomy and calibration content (DEC-0164). Registry state arrives as immutable fingerprinted as-of sets over a passive file-sync hub through one library-owned registry-read port (DEC-0165); data commands are thin fronts over CT-10/CT-15 with per-window license tags (DEC-0166).

### Topology the implementation must preserve

- `COMP-QMB` is middleware in `docs/architecture/dependencies.yaml`, depending on the six backend QMF components and carrying **no** edge to `COMP-QMF-VENUE` — live wiring is trading-node territory. QMB adds no QMF package edge and reverses no dependency direction (DEC-0169).
- QMB is the first sanctioned composition root where the defined-unwired risk contracts it holds (CT-22/23/27/28/29/32) are legally wired, in `world = replay` only; a replay-world verdict can never gate live money (DEC-0162).
- Doors — CLI first, Python API now, MCP after CLI v1 — are thin wrappers over the same pure library functions, with door parity enforced by a tier-2 contract test; `world = simulated` stays reserved-unusable until GAP-0048 (DEC-0159, DEC-0164).

### Entry and exit gate

FEAT-0029's blockers — FEAT-0027 (risk contracts), FEAT-0015 (split-governed data), FEAT-0016 (journal), FEAT-0020 (indicators), FEAT-0022 (structure) — are ordering constraints, not proof any seam is wired. Its exit conditions are implementation-shaped: a golden-slice determinism test reproduces identical CT-32 fingerprints on identical inputs; door parity holds across CLI and Python API; every run ledgers exactly one line (aborted included); `world = simulated` writes refuse; and the `qmb` CLI resolves Books/BMS by fp1 through as-of sets with autocomplete served by the same registry-read port. Until the factory builds and authorizes it, `COMP-QMB` remains non-buildable outside the pipeline, all runs stay world=replay with optimistic-tainted fills spending no split budget and claiming no edge, and human-only promotion remains absolute. The Dukascopy data-licensing question is an open ops item flagged to the operator (DEC-0166; gates governed evidence only).
