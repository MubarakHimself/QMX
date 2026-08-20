---
id: KNOW-TRACEABILITY-QMF-V1
title: QMF V1 Decision, Gap, and Feature Traceability
type: knowledge
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0001, DEC-0003, DEC-0004, DEC-0024, DEC-0120, DEC-0121, DEC-0124, DEC-0125, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0130, DEC-0131, DEC-0132, DEC-0133, DEC-0134, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0140, DEC-0141, DEC-0142]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _docwork/feature_inventory.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, docs/architecture/dependencies.yaml, docs/]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF V1 Decision, Gap, and Feature Traceability

This docs-local locator covers every ledger decision (`DEC-0001` through `DEC-0142`), gap (`GAP-0001` through `GAP-0049`), and inventory feature (`FEAT-0001` through `FEAT-0027`). Statuses are copied from the provisional ledger, gap catalog, and feature inventory; a locator is not ratification or implementation permission. The 2026-08-19/20 foundation architecture sitting ratified `DEC-0099` through `DEC-0125` (AD-1 through AD-21 plus dependency, deferral, and scope rulings) and answered `GAP-0001` through `GAP-0015` and `GAP-0018` through `GAP-0030`; `GAP-0016`/`GAP-0017` are deferred to the backtesting sitting. The 2026-08-20 indicators/structure increment ratified `DEC-0126` through `DEC-0134` (AD-22 through AD-25 plus the increment-gate amendments and the school-neutral and escape-hatch laws) and answered `GAP-0031` through `GAP-0034`. The 2026-08-20 venue sitting ratified `DEC-0135` through `DEC-0142` (AD-26 through AD-28, the cTrader venue facts, the broker-identity ruling, two increment-gate amendment records, and the node-material boundary) and answered `GAP-0035` through `GAP-0038`, leaving `GAP-0039` through `GAP-0046` open — 36 gaps answered, 8 open in total. Recommendations remain non-authorizing evidence, and no row grants credential, external-connection, order, promotion, live-money, restore, deletion, or destructive authority. [DEC-0001] [DEC-0003] [DEC-0004]

## Decision locator — 142 entries

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
| DEC-0067 | `conflict` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Consequences |
| DEC-0068 | `provisional` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
| DEC-0069 | `dead` | [ADR-0009](../decisions/ADR-0009-book-level-paper-mode.md), Options considered |
| DEC-0070 | `provisional` | [ADR-0009](../decisions/ADR-0009-book-level-paper-mode.md), Decision |
| DEC-0071 | `dead` | [ADR-0009](../decisions/ADR-0009-book-level-paper-mode.md), Options considered |
| DEC-0072 | `provisional` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0073 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0074 | `provisional` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0075 | `open` | [QMF Risk](../components/qmf-risk.md), Behavior |
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
| DEC-0094 | `open` | [QMF Risk](../components/qmf-risk.md), Failure modes |
| DEC-0095 | `open` | [QMF Risk](../components/qmf-risk.md), Behavior |
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

## Gap locator — 49 entries

Every row links the full [gap report](../gap-report.md) and the most direct architecture, component, or contract boundary. The foundation architecture sitting `answered` GAP-0001 through GAP-0015 and GAP-0018 through GAP-0030 (answering DEC named per row) and `deferred` GAP-0016/GAP-0017 to the backtesting sitting; the 2026-08-20 indicators/structure increment `answered` GAP-0031 through GAP-0034 (DEC-0126 through DEC-0129); the 2026-08-20 venue sitting `answered` GAP-0035 through GAP-0038 (DEC-0136, DEC-0137, DEC-0135 + DEC-0139, DEC-0138). GAP-0039 through GAP-0046 stay `open`. In total 36 gaps are answered and 8 remain open. `blocking: false` does not turn a recommendation into an answer, and an `answered` row is answered at the ruling level while per-field schema detail may still be documentation-time work.

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
| GAP-0016 | `deferred` | `false` | Deferred by DEC-0121 to the backtesting sitting; [CT-08](../contracts/ct-08-gate-evidence.yaml). Bitemporal ingredients ratified; look-ahead gate not defined here. |
| GAP-0017 | `deferred` | `false` | Deferred by DEC-0121 to the backtesting sitting; [CT-08](../contracts/ct-08-gate-evidence.yaml) |
| GAP-0018 | `answered` | `true` | Answered by DEC-0115 (AD-17); [CT-22](../contracts/ct-22-book-charter.yaml). Multiplicity ratified; full Bot schema is its own sitting. |
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
| GAP-0039 | `open` | `true` | [Gap report](../gap-report.md); [CT-22](../contracts/ct-22-book-charter.yaml) and [CT-23](../contracts/ct-23-risk-evaluation.yaml) |
| GAP-0040 | `open` | `true` | [Gap report](../gap-report.md); [CT-22](../contracts/ct-22-book-charter.yaml) |
| GAP-0041 | `open` | `true` | [Gap report](../gap-report.md); [CT-24](../contracts/ct-24-book-mode.yaml) |
| GAP-0042 | `open` | `true` | [Gap report](../gap-report.md); [CT-25](../contracts/ct-25-risk-journal.yaml) |
| GAP-0043 | `open` | `true` | [Gap report](../gap-report.md); [CT-23](../contracts/ct-23-risk-evaluation.yaml) |
| GAP-0044 | `open` | `true` | [Gap report](../gap-report.md); [CT-23](../contracts/ct-23-risk-evaluation.yaml) |
| GAP-0045 | `open` | `true` | [Gap report](../gap-report.md); [CT-23](../contracts/ct-23-risk-evaluation.yaml) |
| GAP-0046 | `open` | `true` | [Gap report](../gap-report.md); [CT-23](../contracts/ct-23-risk-evaluation.yaml) |
| GAP-0047 | `deferred` | `false` | [Gap report](../gap-report.md); [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md) |
| GAP-0048 | `deferred` | `false` | [Gap report](../gap-report.md); [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md) |
| GAP-0049 | `deferred` | `false` | [Gap report](../gap-report.md); [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md) |

## Feature locator — 27 entries

Waves are the derived dependency waves from `_docwork/feature_inventory.yaml`. The blocker summaries preserve the dependency edges but replace stale wording with the current venue contract topology; they do not declare any blocker complete, and the venue contracts being filled at version 1 does not lift the corpus-wide provisional gate or grant implementation authority.

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
| FEAT-0027 | 10 | [COMP-QMF-RISK](../components/qmf-risk.md) | `planned` | FEAT-0023: ratified venue seam (CT-18 through CT-21, DEC-0135 through DEC-0139); detailed fenced gate below. |

## FEAT-0027 fenced scope and gate

FEAT-0027 is a documentation and reconciliation pass, not a risk implementation pass. It authorizes no Book/BMS runtime, risk decision, exit, order authorization, venue call, account transition, credential use, live-money action, journal handoff, or store write.

### Inputs that must remain unresolved until ruled

- DEC-0040 is now `superseded` by DEC-0115: multiplicity is ratified (a Bot contains one-or-more confluences, recursively, and re-binding never mints a new Bot), so GAP-0018 is answered at the law level. The full Bot/QML schema and the Book binding contract remain their own sittings under GAP-0039.
- DEC-0067 remains `conflict` on exit ownership, and GAP-0040 blocks any exit routing or policy implementation.
- DEC-0069 is `dead`: parallel Bot paper twins must not be revived. DEC-0070 remains provisional study-recap evidence because the direct operator wording is missing; CT-24 is evidence-only until explicit operator confirmation and GAP-0041.
- GAP-0039 through GAP-0046 block Book/BMS schemas, ownership, modes, news control, SQS, formulas, stop-out/benchmark language, and same-tick priority. Recommendations for those gaps remain discussion prompts, not answers.
- The meaning of R stays referenced through `registry:original_risk_unit`; the feature must not restate the registry value or revive dead FORM-0006, DPR, PRS, or legacy capital-slot machinery.

### Topology that the reconciliation must preserve

- Downstream QMF components consume CT-10 from `COMP-QMF-DATA`; `COMP-QMF-DATA-INGEST` and `COMP-QMF-VENUE` may produce CT-10 into Data, but downstream components never depend on Data-Ingest.
- CT-18 and CT-20 are filled at format version 1 by the venue sitting (DEC-0138/DEC-0137) and are no longer reserved; they still carry no active QMF V1 downstream consumer, and their listed Data/Risk consumers are intended only until the factory wires them (GAP-0036/GAP-0038 answered).
- CT-19 is the venue command transport, filled at version 1 by AD-27 (DEC-0137): the four typed command kinds and `fp1` command identity are ratified contract surface. The caller stays unassigned in QMF by design and is assigned to an external out-of-scope QMX application under GAP-0039, so no live command is buildable from QMF alone.
- CT-21 is filled at version 1 by the AD-26 secret lifecycle (DEC-0136) and is no longer a no-operation gate. GAP-0035 is answered, but no credential-bearing integration proceeds until the factory wires and authorizes it — implementation authority arrives only through the factory pipeline.
- CT-22 through CT-25 are reserved and unwired. CT-23 has no caller, CT-24 remains evidence-only pending confirmation and GAP-0041, and CT-25 is not wired to `COMP-QMF-DATA`.

### Entry and exit gate

The inventory edge from FEAT-0023 remains an ordering constraint, not proof that the venue seam is wired. FEAT-0027 may enter drafting only after the ratified venue contracts (CT-18 through CT-21) and their still-unassigned caller and authorization boundary are carried forward without invented active wiring.

The foundation, data, registry, and venue blockers are ratified (GAP-0002 through GAP-0015, GAP-0018 through GAP-0030, and GAP-0035 through GAP-0038; DEC-0099 through DEC-0119 and DEC-0135 through DEC-0139), so FEAT-0027's remaining exit conditions are: an operator ruling on DEC-0067 (exit ownership) and the DEC-0070 evidence caveat, plus the still-open risk gaps GAP-0039 through GAP-0046. The resulting Book/BMS, caller, consumer, state-transition, formula, evidence, and failure contracts must be ratified, and dependency plus registry artifacts must be updated through the documentation change protocol. Until that gate passes, `COMP-QMF-RISK` remains non-buildable, all CT-22 through CT-25 handoffs remain inactive, and human-only promotion remains absolute.
