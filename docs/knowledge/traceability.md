---
id: KNOW-TRACEABILITY-QMF-V1
title: QMF V1 Decision, Gap, and Feature Traceability
type: knowledge
status: ratified
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMB, COMP-QML, COMP-QMN, COMP-QMA-CORE, COMP-QMA-WIRE, COMP-QMA-DAEMON]
decisions: [DEC-0001, DEC-0003, DEC-0004, DEC-0024, DEC-0120, DEC-0121, DEC-0124, DEC-0125, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0130, DEC-0131, DEC-0132, DEC-0133, DEC-0134, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0140, DEC-0141, DEC-0142, DEC-0143, DEC-0144, DEC-0145, DEC-0146, DEC-0147, DEC-0148, DEC-0149, DEC-0150, DEC-0151, DEC-0152, DEC-0153, DEC-0154, DEC-0155, DEC-0156, DEC-0157, DEC-0158, DEC-0159, DEC-0160, DEC-0161, DEC-0162, DEC-0163, DEC-0164, DEC-0165, DEC-0166, DEC-0167, DEC-0168, DEC-0169, DEC-0170, DEC-0171, DEC-0172, DEC-0173, DEC-0174, DEC-0175, DEC-0176, DEC-0177, DEC-0178, DEC-0179, DEC-0180, DEC-0181, DEC-0182, DEC-0183, DEC-0184, DEC-0185, DEC-0186, DEC-0187, DEC-0188, DEC-0189, DEC-0190, DEC-0191, DEC-0192, DEC-0193, DEC-0194, DEC-0195, DEC-0196, DEC-0197, DEC-0198, DEC-0199, DEC-0200, DEC-0201, DEC-0202, DEC-0203, DEC-0204, DEC-0205, DEC-0206, DEC-0207, DEC-0208, DEC-0209, DEC-0210, DEC-0211, DEC-0212, DEC-0213, DEC-0214, DEC-0215, DEC-0216, DEC-0217, DEC-0218, DEC-0219, DEC-0220, DEC-0221, DEC-0222, DEC-0223, DEC-0224, DEC-0225, DEC-0226, DEC-0227, DEC-0228, DEC-0229, DEC-0230, DEC-0231, DEC-0232, DEC-0233, DEC-0234, DEC-0235, DEC-0236, DEC-0237, DEC-0238, DEC-0239, DEC-0240, DEC-0241, DEC-0242, DEC-0243, DEC-0244, DEC-0245, DEC-0246, DEC-0247, DEC-0248, DEC-0249, DEC-0250, DEC-0251, DEC-0252, DEC-0253, DEC-0254, DEC-0255, DEC-0256, DEC-0257, DEC-0258, DEC-0259, DEC-0260, DEC-0261, DEC-0262, DEC-0300, DEC-0301, DEC-0302, DEC-0303, DEC-0304, DEC-0305, DEC-0306, DEC-0307, DEC-0308, DEC-0309, DEC-0310, DEC-0311, DEC-0312, DEC-0313, DEC-0314, DEC-0315, DEC-0316, DEC-0317, DEC-0318, DEC-0319, DEC-0320, DEC-0321, DEC-0322, DEC-0323, DEC-0324, DEC-0325, DEC-0326, DEC-0327, DEC-0328, DEC-0329, DEC-0330, DEC-0331, DEC-0332, DEC-0333, DEC-0334, DEC-0335, DEC-0336, DEC-0337, DEC-0338, DEC-0339, DEC-0340, DEC-0341, DEC-0342, DEC-0343, DEC-0344, DEC-0345, DEC-0346, DEC-0347, DEC-0348, DEC-0349, DEC-0350, DEC-0360, DEC-0361, DEC-0362, DEC-0363, DEC-0364, DEC-0365, DEC-0366, DEC-0367, DEC-0368, DEC-0369, DEC-0370, DEC-0371, DEC-0372, DEC-0373, DEC-0374, DEC-0375, DEC-0376, DEC-0377, DEC-0378, DEC-0379]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _docwork/feature_inventory.yaml, _docwork/manifest.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/.memlog.md, docs/decisions/ADR-0017-qmb-experimentation-library.md, docs/decisions/ADR-0018-qml-bot-authoring-library.md, docs/decisions/ADR-0019-trading-node.md, docs/components/trading-node.md, docs/architecture/dependencies.yaml, docs/]
generated: 2026-08-18
verified: '2026-08-30'
stale_after: 30d
---

# QMF V1 Decision, Gap, and Feature Traceability

This docs-local locator covers every ledger decision (`DEC-0001`–`DEC-0185`, `DEC-0186`–`DEC-0262`, `DEC-0300`–`DEC-0350` and `DEC-0360`–`DEC-0379`), gap (`GAP-0001`–`GAP-0058` and `GAP-0070`–`GAP-0091`), and inventory feature (`FEAT-0001`–`FEAT-0030` and `FEAT-0040`–`FEAT-0046`). Statuses are copied from the provisional ledger, gap catalog, and feature inventory; a locator is not ratification or implementation permission. The 2026-08-19/20 foundation architecture sitting ratified `DEC-0099` through `DEC-0125` (AD-1 through AD-21 plus dependency, deferral, and scope rulings) and answered `GAP-0001` through `GAP-0015` and `GAP-0018` through `GAP-0030`; `GAP-0016`/`GAP-0017` are deferred to the backtesting sitting. The 2026-08-20 indicators/structure increment ratified `DEC-0126` through `DEC-0134` (AD-22 through AD-25 plus the increment-gate amendments and the school-neutral and escape-hatch laws) and answered `GAP-0031` through `GAP-0034`. The 2026-08-20 venue sitting ratified `DEC-0135` through `DEC-0142` (AD-26 through AD-28, the cTrader venue facts, the broker-identity ruling, two increment-gate amendment records, and the node-material boundary) and answered `GAP-0035` through `GAP-0038`. The 2026-08-20 risk sitting ratified `DEC-0143` through `DEC-0158` (AD-29 through AD-41, the cross-AD amendments to AD-7/10/12/16/17/18/21/24/27/28, and the corpus-precedence and configurable-means-UI standing laws) and answered `GAP-0039` through `GAP-0046`. The 2026-08-20/21 **QMB increment** ratified `DEC-0159` through `DEC-0169` (the QMB child spine B-1 through B-15 plus the click/optuna stack pins and full adoption by delegation) and folded `COMP-QMB` — the experimentation/backtesting library and `qmb` CLI, an application-layer product built ON QMF (ADR-0017, `FEAT-0029`); it partially closed `GAP-0048` (seams ruled), delivered look-ahead prevention for the deferred `GAP-0016`/`GAP-0017`, and advanced `GAP-0049` without closing it. The 2026-08-21 **QML increment** ratified `DEC-0171` through `DEC-0184` (the QML child spine QL-1 through QL-10 at `architecture-QML-2026-08-21/`, status FINAL, run autonomously by operator delegation with a 5-lens reviewer gate applied) and folded `COMP-QML` — the bot-authoring application-layer library built ON QMF (ADR-0018, `FEAT-0030`) — answering `GAP-0047`, with the 2026-08-21 operator veto round then confirming all six delegation-made calls kept and recording two expansion riders as `DEC-0185`; 45 gaps answered, 0 open in total, with `GAP-0016`/`GAP-0017` (registration gate, DEC-0121), `GAP-0048` content, and `GAP-0049` still deferred. The 2026-08-28 **trading-node sitting** ratified `DEC-0186` through `DEC-0260` — the trading node's child spine TN-1 through TN-25 at `architecture-NODE-2026-08-28/`, status FINAL, plus its 20 first-gate rulings and 34 GATE-2 rulings, four direct operator rulings (R1 no operator command line, R2 the soak as one full unattended week with a separate zero-authority observability stack, R3 promotion a click with activation a second act, R4 free news only), the parent annotations, and the spine-adoption umbrella (`DEC-0259`) ratified by operator delegation plus those four direct rulings — and folded `COMP-QMN` (ADR-0019, `FEAT-0031`), the supervised composition-root runtime built ON QMF and the sole sanctioned wirer of `qmf-venue`; it answered no catalog gap and raised eight new ones (`GAP-0050` through `GAP-0056` deferred, `GAP-0057` a non-blocking `open` cheap-veto item), and passed a six-lens first gate and a five-lens validation re-gate with a final certification seat. The 2026-08-30 documentation-factory veto round then closed that increment's cheap-veto surface by direct operator rulings recorded as `DEC-0261` and `DEC-0262`: `GAP-0057` moves to `answered` (no per-bot warm-up on the node, the inherited admission row stands) and a ninth node gap `GAP-0058` (the placement variants) is `open` and IN SCOPE, ruled at the second exchange (`DEC-0262`). In total 46 gaps answered and 0 blocking open, with `GAP-0016`/`GAP-0017`, `GAP-0048`/`GAP-0049` and the node rows `GAP-0050`–`GAP-0056` deferred, `GAP-0057` answered and `GAP-0058` open (non-blocking, in scope). Recommendations remain non-authorizing evidence, and no row grants credential, external-connection, order, promotion, live-money, restore, deletion, or destructive authority. [DEC-0001] [DEC-0003] [DEC-0004]

## Decision locator — 333 entries

The locator names the primary docs-local document and section. `dead`, `superseded`, `conflict`, `open`, and `out-of-scope` statuses are preserved so later agents do not revive or silently settle them. Decisions `DEC-0099` through `DEC-0125` were ratified at the foundation architecture sitting; their authoritative source is the ratified [architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), and their absorbed content lands in the lens, component, and contract docs cited below.

| Decision | Status | Primary document and section |
|---|---|---|
| DEC-0001 | `ratified` | [ADR-0001](../decisions/ADR-0001-authority-and-document-first.md), Decision |
| DEC-0002 | `ratified` | [ADR-0001](../decisions/ADR-0001-authority-and-document-first.md), Decision |
| DEC-0003 | `ratified` | [ADR-0001](../decisions/ADR-0001-authority-and-document-first.md), Decision |
| DEC-0004 | `ratified` | [ADR-0001](../decisions/ADR-0001-authority-and-document-first.md), Decision |
| DEC-0005 | `ratified` | [Operations runbook](../lenses/ops/runbook.md), Permission boundary |
| DEC-0006 | `ratified` | [Constitution](../constitution.md), Laws |
| DEC-0007 | `ratified` | [Constitution](../constitution.md), Laws |
| DEC-0008 | `ratified` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0009 | `ratified` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0010 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0011 | `ratified` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0012 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0013 | `ratified` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0014 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0015 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0016 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0017 | `ratified` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0018 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0019 | `ratified` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0020 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0021 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0022 | `ratified` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0023 | `dead` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Options considered |
| DEC-0024 | `ratified` | [ADR-0002](../decisions/ADR-0002-toolbox-and-v1-roster.md), Decision |
| DEC-0025 | `ratified` | [SCN-0001](../scenarios/SCN-0001-core-freeze-gate.md), Core freeze gate |
| DEC-0026 | `ratified` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0027 | `ratified` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0028 | `ratified` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0029 | `ratified` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0030 | `ratified` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0031 | `ratified` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Decision |
| DEC-0032 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), freeze-choice status (superseded by DEC-0124) |
| DEC-0033 | `ratified` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0034 | `dead` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Options considered |
| DEC-0035 | `ratified` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0036 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-16 (superseded by DEC-0114) |
| DEC-0037 | `dead` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Options considered |
| DEC-0038 | `ratified` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0039 | `ratified` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0040 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-17 (superseded by DEC-0115) |
| DEC-0041 | `ratified` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0042 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0043 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-19 (superseded by DEC-0117) |
| DEC-0044 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0045 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0046 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0047 | `superseded` | [Architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md), AD-19 (superseded by DEC-0117) |
| DEC-0048 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0049 | `ratified` | [Gap report](../gap-report.md); ruled by the operator 2026-08-21 (EXT-2093) — scoped entry-blocking detector pause, L39 preserved |
| DEC-0050 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0051 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0052 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0053 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0054 | `ratified` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0055 | `ratified` | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md), Decision |
| DEC-0056 | `superseded` | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md), superseded by DEC-0128 |
| DEC-0057 | `out-of-scope` | [Gap report](../gap-report.md), Out-of-scope topics |
| DEC-0058 | `ratified` | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md), Decision |
| DEC-0059 | `ratified` | [ADR-0007](../decisions/ADR-0007-venue-neutral-integration.md), Decision |
| DEC-0060 | `ratified` | [ADR-0007](../decisions/ADR-0007-venue-neutral-integration.md), Decision |
| DEC-0061 | `ratified` | [ADR-0007](../decisions/ADR-0007-venue-neutral-integration.md), Decision |
| DEC-0062 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0063 | `dead` | [QMF Venue](../components/qmf-venue.md), Authority boundary |
| DEC-0064 | `out-of-scope` | [QMF Venue](../components/qmf-venue.md), Authority boundary |
| DEC-0065 | `ratified` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
| DEC-0066 | `ratified` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
| DEC-0067 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0147, AD-33) |
| DEC-0068 | `ratified` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
| DEC-0069 | `dead` | [ADR-0009](../decisions/ADR-0009-book-level-paper-mode.md), Options considered |
| DEC-0070 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (confirmed and subsumed by DEC-0149, AD-35) |
| DEC-0071 | `dead` | [ADR-0009](../decisions/ADR-0009-book-level-paper-mode.md), Options considered |
| DEC-0072 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0152, AD-38) |
| DEC-0073 | `dead` | [Gap report](../gap-report.md), Dead decisions |
| DEC-0074 | `ratified` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0075 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0153, AD-39) |
| DEC-0076 | `ratified` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0077 | `dead` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Options considered |
| DEC-0078 | `ratified` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0079 | `dead` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Options considered |
| DEC-0080 | `ratified` | [ADR-0008](../decisions/ADR-0008-book-and-risk-boundary.md), Decision |
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
| DEC-0092 | `ratified` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Decision |
| DEC-0093 | `dead` | [ADR-0010](../decisions/ADR-0010-risk-vocabulary-clean-start.md), Options considered |
| DEC-0094 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0155, AD-41) |
| DEC-0095 | `superseded` | [Gap report](../gap-report.md), Superseded baseline chains (superseded by DEC-0143, AD-29) |
| DEC-0096 | `ratified` | [Constitution](../constitution.md), Laws |
| DEC-0097 | `ratified` | [Constitution](../constitution.md), Laws |
| DEC-0098 | `ratified` | [Performance budgets](../lenses/performance/budgets.md), Baselines |

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
| DEC-0142 | `ratified` | Node-material boundary (pointer-only boundary SUPERSEDED IN PART 2026-08-29, DEC-0259) | [Trading node](../components/trading-node.md) (COMP-QMN, where trading-node runtime material now lives); [ADR-0019](../decisions/ADR-0019-trading-node.md); [QMF Venue](../components/qmf-venue.md), Authority boundary; `tracker/trading-node-notes.md` now history |

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

### Trading-node increment decisions — DEC-0186 through DEC-0262

These decisions were ratified at the 2026-08-28 trading-node child architecture sitting (child spine TN-1 through TN-25, `architecture-NODE-2026-08-28/`, status FINAL, ratified by operator delegation plus four direct rulings). `TN-N` is the node spine invariant each `DEC-0186` through `DEC-0210` carries; `DEC-0211` through `DEC-0215` are the four direct operator rulings R1–R4 plus the same round's also-ruled items; `DEC-0216` through `DEC-0235` are the 20 first-gate rulings that changed behaviour; `DEC-0236` is the GATE-2 umbrella (34 rulings applied at desk by residual fix pass 2, TN ids stable); `DEC-0237` through `DEC-0240` carry the KSA vocabulary re-ratification, the PRD §6 mined doctrine, the PRD §10 dispositions and the ticket 006 trendbar-basis ruling; `DEC-0241` through `DEC-0258` are the parent annotations, each tagged applied, recorded-not-applied, or proposed exactly as the spine's "Parent annotations and mints" section records it; `DEC-0259` is the spine-adoption umbrella and `DEC-0260` the open-items register; `DEC-0261` and `DEC-0262` are the later 2026-08-30 documentation-factory veto-round closeout in two exchanges (operator-direct, closing the `DEC-0259` cheap-veto surface — `DEC-0261` the first exchange, `DEC-0262` the second, ruling the two placement variants in scope and the MIS labeler catalog with training the last node epic) and are ratified at that veto round rather than at the 2026-08-28 sitting. QMF spine AD-1 through AD-41 binds read-only as the parent, and QMB B-1 through B-15 and QML QL-1 through QL-10 are honoured read-only; the node adds no QMF package edge and reverses no dependency direction — nothing imports `qmn`. The authoritative source is the [node architecture spine](../../_bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md) (`SRC-11`) grounded on the 2026-08-28 sitting transcript `archive/trading-node.txt` (`SRC-12`, the operator's own-words surface only), and ledger entries `DEC-0186` through `DEC-0260`. The primary document names where the absorbed content lands docs-local. Every entry carries `authority: rider` (delegation plus the four direct rulings); the component spec being written for `COMP-QMN` is [trading-node](../components/trading-node.md) and the point-in-time ADR is [ADR-0019](../decisions/ADR-0019-trading-node.md).

| Decision | Status | Spine | Primary document |
|---|---|---|---|
| DEC-0186 | `ratified` | TN-1 | [Trading node](../components/trading-node.md), TN-1 (identity, packaging, base branch); [ADR-0019](../decisions/ADR-0019-trading-node.md) |
| DEC-0187 | `ratified` | TN-2 | [Trading node](../components/trading-node.md), TN-2 (composition root and boot ceremony) |
| DEC-0188 | `ratified` | TN-3 | [Trading node](../components/trading-node.md), TN-3 (topology, planes, trust boundaries); [Overview](../architecture/overview.md) |
| DEC-0189 | `ratified` | TN-4 | [Trading node](../components/trading-node.md), TN-4 (process model, supervision, shutdown contract) |
| DEC-0190 | `ratified` | TN-5 | [Trading node](../components/trading-node.md), TN-5 (the live loop, push-to-pull accumulator) |
| DEC-0191 | `ratified` | TN-6 | [Trading node](../components/trading-node.md), TN-6 (the order path) |
| DEC-0192 | `ratified` | TN-7 | [Trading node](../components/trading-node.md), TN-7 (KSA protection authority, kill switch) |
| DEC-0193 | `ratified` | TN-8 | [Trading node](../components/trading-node.md), TN-8 (risk protection set, node value roster) |
| DEC-0194 | `ratified` | TN-9 | [Trading node](../components/trading-node.md), TN-9 (paper mode and the soak week) |
| DEC-0195 | `ratified` | TN-10 | [Trading node](../components/trading-node.md), TN-10 (startup, recovery, explained drift) |
| DEC-0196 | `ratified` | TN-11 | [Trading node](../components/trading-node.md), TN-11 (venue integration on cTrader) |
| DEC-0197 | `ratified` | TN-12 | [Trading node](../components/trading-node.md), TN-12 (secrets); [Security model](../lenses/security/security-model.md) |
| DEC-0198 | `ratified` | TN-13 | [Trading node](../components/trading-node.md), TN-13 (live data, news calendar, backup, restore drills) |
| DEC-0199 | `ratified` | TN-14 | [Trading node](../components/trading-node.md), TN-14 (time discipline at the live boundary) |
| DEC-0200 | `ratified` | TN-15 | [Trading node](../components/trading-node.md), TN-15 (observability); [Logging spec](../lenses/observability/logging-spec.md); [Metrics and alerts](../lenses/observability/metrics-and-alerts.md) |
| DEC-0201 | `ratified` | TN-16 | [Trading node](../components/trading-node.md), TN-16 (deployment, CI, rollback); [Operations runbook](../lenses/ops/runbook.md) |
| DEC-0202 | `ratified` | TN-17 | [Trading node](../components/trading-node.md), TN-17 (doors: three thin doors, no command line) |
| DEC-0203 | `ratified` | TN-18 | [Trading node](../components/trading-node.md), TN-18 (config surface, UI-editable by design) |
| DEC-0204 | `ratified` | TN-19 | [Trading node](../components/trading-node.md), TN-19 (bot seats, runtime-protocol hosting, MIS seam) |
| DEC-0205 | `ratified` | TN-20 | [Trading node](../components/trading-node.md), TN-20 (promotion and activation, two acts) |
| DEC-0206 | `ratified` | TN-21 | [Trading node](../components/trading-node.md), TN-21 (replay mode, the node's regression tool) |
| DEC-0207 | `ratified` | TN-22 | [Trading node](../components/trading-node.md), TN-22 (multi-account/multi-broker seam) |
| DEC-0208 | `ratified` | TN-23 | [Trading node](../components/trading-node.md), TN-23 (QA standard, benchmarks, soak acceptance) |
| DEC-0209 | `ratified` | TN-24 | [Trading node](../components/trading-node.md), TN-24 (position-safety closures) |
| DEC-0210 | `ratified` | TN-25 | [Trading node](../components/trading-node.md), TN-25 (accounting boundary, virtual ledger) |
| DEC-0211 | `ratified` | R1 | [ADR-0019](../decisions/ADR-0019-trading-node.md), Decision (no operator command line); [Trading node](../components/trading-node.md), TN-17; [Operations runbook](../lenses/ops/runbook.md) |
| DEC-0212 | `ratified` | R2 | [ADR-0019](../decisions/ADR-0019-trading-node.md), Decision (soak week, observability stack); [Trading node](../components/trading-node.md), TN-9/TN-15; [Metrics and alerts](../lenses/observability/metrics-and-alerts.md) |
| DEC-0213 | `ratified` | R3 | [ADR-0019](../decisions/ADR-0019-trading-node.md), Decision (promotion a click, activation second); [Trading node](../components/trading-node.md), TN-20 |
| DEC-0214 | `ratified` | R4 | [ADR-0019](../decisions/ADR-0019-trading-node.md), Decision (free news only); [Trading node](../components/trading-node.md), TN-13 |
| DEC-0215 | `ratified` | Also ruled | [ADR-0019](../decisions/ADR-0019-trading-node.md), Decision (UI, MIS training, extensibility, alpha decay); [Trading node](../components/trading-node.md), TN-19 |
| DEC-0216 | `ratified` | Gate ruling 1 | [Trading node](../components/trading-node.md), TN-8/TN-25 (the kill-line input series) |
| DEC-0217 | `ratified` | Gate ruling 2 | [Trading node](../components/trading-node.md), TN-12/TN-13; [CT-14](../contracts/ct-14-backup-restore.yaml); [Security model](../lenses/security/security-model.md) |
| DEC-0218 | `ratified` | Gate ruling 3 | [Trading node](../components/trading-node.md), TN-4/TN-7 (never-auto predicates, node stand-down) |
| DEC-0219 | `ratified` | Gate ruling 4 | [Trading node](../components/trading-node.md), TN-11/TN-22/TN-25 (netting or hedging measured) |
| DEC-0220 | `ratified` | Gate ruling 5 | [Trading node](../components/trading-node.md), TN-17 (second command-line question, overtaken by R1); [ADR-0019](../decisions/ADR-0019-trading-node.md) |
| DEC-0221 | `ratified` | Gate ruling 6 | [Trading node](../components/trading-node.md), TN-6/TN-7; [Constitution](../constitution.md), Laws (L39 exit preservation) |
| DEC-0222 | `ratified` | Gate ruling 7 | [Trading node](../components/trading-node.md), TN-12; [Security model](../lenses/security/security-model.md) (rotation by credential reference) |
| DEC-0223 | `ratified` | Gate ruling 8 | [Trading node](../components/trading-node.md), TN-18 (config eligibility/identity only; runtime state a fold) |
| DEC-0224 | `ratified` | Gate ruling 9 | [Trading node](../components/trading-node.md), TN-5/TN-6 (command ordinal versus journal sequence) |
| DEC-0225 | `ratified` | Gate ruling 10 | [Trading node](../components/trading-node.md), TN-10/TN-25; [CT-01](../contracts/ct-01-money-quantity.yaml) (exact scaled-integer domain) |
| DEC-0226 | `ratified` | Gate ruling 11 | [Trading node](../components/trading-node.md), TN-2/TN-4 (supervision mechanics, the safe point) |
| DEC-0227 | `ratified` | Gate ruling 12 | [Trading node](../components/trading-node.md), TN-12/TN-16; [Security model](../lenses/security/security-model.md) (qmx service account, four secret holders) |
| DEC-0228 | `ratified` | Gate ruling 13 | [Trading node](../components/trading-node.md), TN-11; [ADR-0019](../decisions/ADR-0019-trading-node.md) (node mints VenueClientPort) |
| DEC-0229 | `ratified` | Gate ruling 14 | [Trading node](../components/trading-node.md), TN-21 (one sanctioned cross-world import port) |
| DEC-0230 | `ratified` | Gate ruling 15 | [Trading node](../components/trading-node.md), TN-8/TN-19 (SQS via the signal snapshot, keyed baseline) |
| DEC-0231 | `ratified` | Gate ruling 16 | [Trading node](../components/trading-node.md), TN-17/TN-18 (value-status, pre-SOAK); [Gap report](../gap-report.md), GAP-0050 |
| DEC-0232 | `ratified` | Gate ruling 17 | [Trading node](../components/trading-node.md), TN-25 (TN-25 minted: accounting boundary and virtual ledger) |
| DEC-0233 | `ratified` | Gate ruling 18 | [Metrics and alerts](../lenses/observability/metrics-and-alerts.md); [Trading node](../components/trading-node.md), TN-15 (silent-degradation class, dead-man's switch) |
| DEC-0234 | `ratified` | Gate ruling 19 | [Trading node](../components/trading-node.md), TN-17; [Security model](../lenses/security/security-model.md) (SO_PEERCRED powers authentication) |
| DEC-0235 | `ratified` | Gate ruling 20 | [Trading node](../components/trading-node.md), TN-8/TN-9 (the paper ledger, kill line drillable before live) |
| DEC-0236 | `ratified` | GATE-2 umbrella | [ADR-0019](../decisions/ADR-0019-trading-node.md); [Trading node](../components/trading-node.md) (34 GATE-2 rulings applied at desk, TN ids stable) |
| DEC-0237 | `ratified` | KSA re-ratification | [Trading node](../components/trading-node.md), TN-7; [Gap report](../gap-report.md), GAP-0050; [Constitution](../constitution.md), Laws (L37 GitBook baseline) |
| DEC-0238 | `ratified` | PRD §6 mined doctrine | [Trading node](../components/trading-node.md), TN-10/TN-13; [ADR-0019](../decisions/ADR-0019-trading-node.md) |
| DEC-0239 | `ratified` | PRD §10 rows 12-15 | [Trading node](../components/trading-node.md), TN-24; [ADR-0019](../decisions/ADR-0019-trading-node.md) |
| DEC-0240 | `ratified` | Ticket 006 | [Trading node](../components/trading-node.md), TN-11; [cTrader](../components/ctrader.md) (trendbar basis measured per broker) |
| DEC-0241 | `ratified` | Annotation L30 [APPLIED] | [Constitution](../constitution.md), Laws (L30 — qmn.venue the sanctioned qmf-venue import boundary) |
| DEC-0242 | `ratified` | Annotation AD-28 [RECORDED-NOT-APPLIED] | [Trading node](../components/trading-node.md), TN-11; [QMF Venue](../components/qmf-venue.md) |
| DEC-0243 | `ratified` | Annotation async exemption [APPLIED] | [Constitution](../constitution.md), Laws (L30/AD-15); [QMF Venue](../components/qmf-venue.md); [Trading node](../components/trading-node.md), TN-11 |
| DEC-0244 | `ratified` | Annotation SessionTopology [APPLIED] | [QMF Venue](../components/qmf-venue.md) (connection count derived from the roster) |
| DEC-0245 | `ratified` | Annotation README correction [APPLIED] | [QMF Venue](../components/qmf-venue.md) (stale README corrected as a factory item) |
| DEC-0246 | `ratified` | Annotation CT-13/CT-25 bridge [APPLIED] | [CT-25](../contracts/ct-25-risk-journal.yaml); [CT-13](../contracts/ct-13-journal.yaml); [Logging spec](../lenses/observability/logging-spec.md) |
| DEC-0247 | `ratified` | Annotation CT-20 mapping rows [APPLIED] | [CT-20](../contracts/ct-20-venue-event.yaml) (position and balance read-back observations) |
| DEC-0248 | `ratified` | Annotation CT-20 lifecycle-stop [RECORDED-NOT-APPLIED] | [CT-20](../contracts/ct-20-venue-event.yaml); [Trading node](../components/trading-node.md), TN-4 |
| DEC-0249 | `ratified` | Annotation node_resurrect [APPLIED] | [CT-13](../contracts/ct-13-journal.yaml); [CT-30](../contracts/ct-30-control-action.yaml); [Trading node](../components/trading-node.md), TN-4 |
| DEC-0250 | `ratified` | Annotation CT-30 predicates [APPLIED] | [CT-30](../contracts/ct-30-control-action.yaml) (satisfaction-predicate declarations per matrix cell) |
| DEC-0251 | `ratified` | Annotation CT-24/CT-28 [APPLIED] | [CT-24](../contracts/ct-24-book-mode.yaml); [CT-28](../contracts/ct-28-book-binding.yaml); [Trading node](../components/trading-node.md), TN-25 |
| DEC-0252 | `ratified` | Annotation CT-14 [APPLIED] | [CT-14](../contracts/ct-14-backup-restore.yaml); [Security model](../lenses/security/security-model.md); [Trading node](../components/trading-node.md), TN-12/TN-13 |
| DEC-0253 | `ratified` | Annotation AD-19 sealed-archive [APPLIED] | [qmf-data](../components/qmf-data.md), sealed-archive; [CT-14](../contracts/ct-14-backup-restore.yaml); [Trading node](../components/trading-node.md), TN-3 |
| DEC-0254 | `ratified` | Annotation value_status_required [APPLIED] | [variables registry](../registry/variables.yaml); [Trading node](../components/trading-node.md), TN-18 |
| DEC-0255 | `ratified` | Annotation kill_line = loss_floor [APPLIED] | [variables registry](../registry/variables.yaml); [Trading node](../components/trading-node.md), TN-8 |
| DEC-0256 | `ratified` | Registry mint table [APPLIED] | [variables registry](../registry/variables.yaml) (every node-minted row configurable, unit-kinded, blank-effect tagged) |
| DEC-0257 | `ratified` | Annotation PRD §3 allow-list [PROPOSED] | [Metrics and alerts](../lenses/observability/metrics-and-alerts.md); [Gap report](../gap-report.md), Open operator items |
| DEC-0258 | `ratified` | Four reconciliation verdicts [APPLIED] | [Trading node](../components/trading-node.md), TN-10; [CT-20](../contracts/ct-20-venue-event.yaml) |
| DEC-0259 | `ratified` | Spine-adoption umbrella | [ADR-0019](../decisions/ADR-0019-trading-node.md); [Trading node](../components/trading-node.md); [Gap report](../gap-report.md); [Changelog](../changelog.md) |
| DEC-0260 | `ratified` | Open-items register | [Gap report](../gap-report.md), Open operator items; [Trading node](../components/trading-node.md) |
| DEC-0261 | `ratified` | Veto-round closeout (2026-08-30) | [ADR-0019](../decisions/ADR-0019-trading-node.md), dated follow-up; [Trading node](../components/trading-node.md), TN-9/TN-20 (bot journey, no per-bot warm-up, next-day activation, liveness heartbeat); [Gap report](../gap-report.md), GAP-0057 answered / GAP-0058; [Changelog](../changelog.md), 2026-08-30 entry |
| DEC-0262 | `ratified` | Two placement variants in scope; MIS last epic with the labeler catalog (2026-08-30, second exchange) | [ADR-0019](../decisions/ADR-0019-trading-node.md), dated follow-up; [Trading node](../components/trading-node.md), TN-3/TN-16/TN-19 (placement variants, self-setup, MIS labeler catalog); [Gap report](../gap-report.md), GAP-0058 open, in scope / GAP-0051 labeler-catalog note; [Changelog](../changelog.md), 2026-08-30 entry |

GAP-0050 through GAP-0056 are `deferred` by the node sitting and GAP-0057 was raised as a non-blocking `open` cheap-veto item, then `answered` at the 2026-08-30 veto round (`DEC-0261`, no per-bot warm-up on the node); a ninth node gap GAP-0058 (the placement variants) was recorded `deferred` in that round's first exchange and then ruled `open` and IN SCOPE in the second, its design owed by a one-shot architecture increment before the variant's epic (`DEC-0262`); the sitting itself answered no catalog gap (`DEC-0259`, `DEC-0260`, `DEC-0261`, `DEC-0262`). DEC-0262 also corrects the increment's earlier "the corpus names no models": the MIS labeler catalog is eight ratified labelers (six rule-based, the fitted `liquidity_stress_v1`, the trained `regime_classifier_v1` still design-owed), with MIS training the LAST node epic run as an offline operator-run script (GAP-0051 labeler-catalog note). DEC-0192 (TN-7) closes the KSA matrix SHAPE and DEC-0237 re-ratifies the KSA vocabulary from the GitBook baseline, while the per-cell VALUES stay open under GAP-0050 (never GAP-0015, which is the lineage-edges gap answered 2026-08-20 by DEC-0114). DEC-0231 and DEC-0254 add value-status discipline and the `value_status_required` registry schema field; DEC-0255 records that `kill_line_capital_floor` IS AD-40's `loss_floor` (one variable, one name). DEC-0243 is the one delegated impurity applied as a declared exemption to the QMF async-conformance test for `qmf.venue.connection`, with its refusal path pre-ruled (the transport increment moves into `qmn.venue.ctrader`); DEC-0242 and DEC-0248 are recorded-not-applied candidate parent amendments — a child never amends a parent by assertion. DEC-0257 is PROPOSED (the PRD §3 notification allow-list widening), ratified by this increment by default under the cheap-veto posture and then SETTLED by DEC-0261 (the silent-degradation class accepted, the external watcher kept and renamed the **liveness heartbeat**, the daily liveness digest rejected). DEC-0261 also rules the bot journey binding across the corpus (no per-bot warm-up on the node; bots arrive backtested, paper-tested outside the node and operator-approved) and the next-day-activation rule at the account-scoped day-boundary calendar (DEC-0210). Every node DEC carries `authority: rider`; nothing in these entries grants credential, order, promotion, activation, live-money, or destructive authority — that arrives only through the factory pipeline.

### QMA increment decisions — DEC-0300 through DEC-0350, DEC-0360 through DEC-0379

These decisions were ratified at the 2026-08-28/29 QMX agentic-system child architecture sitting (spine AD-1 through AD-29, `architecture-QMA-2026-08-28/`, status FINAL, validation closed dry 2026-08-29, absorbed by operator delegation via the job-spec rider `SRC-15`). `AD-N` is the QMA spine invariant each carries where one applies; QMF spine AD-1 through AD-41 binds read-only as the parent. The QMX agentic system (QMA) is an application-layer consumer built ON QMF — the daemon plus the QMA SDK plus the wire contract — so these decisions add no QMF package edge and reverse no dependency direction. DEC-0300 through DEC-0328 carry AD-1 through AD-29; DEC-0329 is the spine-adoption umbrella; DEC-0330 through DEC-0350 are the naming, scope, ledger and money-path rulings; DEC-0360 through DEC-0379 are the Cut-outright table minted `status: dead`.

| Decision | Status | Spine | Primary document |
|---|---|---|---|
| DEC-0300 | `ratified` | AD-1 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-core](../components/qma-core.md); [CT-42](../contracts/ct-42-qma-plugin-manifest-context.yaml) |
| DEC-0301 | `ratified` | AD-2 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-core](../components/qma-core.md); [dependencies](../architecture/dependencies.yaml) |
| DEC-0302 | `ratified` | AD-3 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-core](../components/qma-core.md) |
| DEC-0303 | `ratified` | AD-4 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [Stack](../architecture/stack.md) |
| DEC-0304 | `ratified` | AD-5 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-wire](../components/qma-wire.md); [CT-40](../contracts/ct-40-qma-wire-envelope.yaml) |
| DEC-0305 | `ratified` | AD-6 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0306 | `ratified` | AD-7 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-core](../components/qma-core.md); [Glossary](../glossary.md) |
| DEC-0307 | `ratified` | AD-8 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0308 | `ratified` | AD-9 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-51](../contracts/ct-51-qma-task-ledger-entry.yaml) |
| DEC-0309 | `ratified` | AD-10 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-41](../contracts/ct-41-qma-hook-event-result.yaml) |
| DEC-0310 | `ratified` | AD-11 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-41](../contracts/ct-41-qma-hook-event-result.yaml) |
| DEC-0311 | `ratified` | AD-12 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0312 | `ratified` | AD-13 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0313 | `ratified` | AD-14 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0314 | `ratified` | AD-15 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-45](../contracts/ct-45-qma-model-deployment-broker.yaml) |
| DEC-0315 | `ratified` | AD-16 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [SCN-0014](../scenarios/SCN-0014-money-path-barrier.md) |
| DEC-0316 | `ratified` | AD-17 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-46](../contracts/ct-46-qma-execution-environment-job.yaml) |
| DEC-0317 | `ratified` | AD-18 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-43](../contracts/ct-43-qma-memory-provider.yaml) |
| DEC-0318 | `ratified` | AD-19 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-44](../contracts/ct-44-qma-knowledge-source.yaml) |
| DEC-0319 | `ratified` | AD-20 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-48](../contracts/ct-48-qma-mailbox-envelope.yaml) |
| DEC-0320 | `ratified` | AD-21 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-42](../contracts/ct-42-qma-plugin-manifest-context.yaml) |
| DEC-0321 | `ratified` | AD-22 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-50](../contracts/ct-50-qma-refinement-proposal.yaml) |
| DEC-0322 | `ratified` | AD-23 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [Metrics and alerts](../lenses/observability/metrics-and-alerts.md) |
| DEC-0323 | `ratified` | AD-24 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [Security model](../lenses/security/security-model.md) |
| DEC-0324 | `ratified` | AD-25 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0325 | `ratified` | AD-26 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [variables registry](../registry/variables.yaml) |
| DEC-0326 | `ratified` | AD-27 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0327 | `ratified` | AD-28 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [SCN-0014](../scenarios/SCN-0014-money-path-barrier.md) |
| DEC-0328 | `ratified` | AD-29 | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-49](../contracts/ct-49-qma-routine.yaml) |
| DEC-0329 | `ratified` | Spine-adoption umbrella | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Gap report](../gap-report.md); [Changelog](../changelog.md) |
| DEC-0330 | `ratified` | QMA naming | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Glossary](../glossary.md) |
| DEC-0331 | `ratified` | Quant replaces Bot | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Glossary](../glossary.md); [qma-core](../components/qma-core.md) |
| DEC-0332 | `ratified` | Fresh start; multi-agent | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md) |
| DEC-0333 | `ratified` | Build priority; first milestone | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-wire](../components/qma-wire.md) |
| DEC-0334 | `ratified` | One Python daemon; stack pins | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Stack](../architecture/stack.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0335 | `ratified` | Contract-hub house style | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-core](../components/qma-core.md) |
| DEC-0336 | `ratified` | Deployment envelope | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0337 | `ratified` | Namespace `qma.*` | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Glossary](../glossary.md); [qma-core](../components/qma-core.md) |
| DEC-0338 | `ratified` | Task-level ledgers | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-51](../contracts/ct-51-qma-task-ledger-entry.yaml) |
| DEC-0339 | `ratified` | Hooks on every primitive | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-41](../contracts/ct-41-qma-hook-event-result.yaml) |
| DEC-0340 | `ratified` | Three control primitives | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md) |
| DEC-0341 | `ratified` | No execution tool; reachability barrier | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [SCN-0014](../scenarios/SCN-0014-money-path-barrier.md) |
| DEC-0342 | `ratified` | No memory engine in-house | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-43](../contracts/ct-43-qma-memory-provider.yaml) |
| DEC-0343 | `ratified` | Read-only Knowledge corpus | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-44](../contracts/ct-44-qma-knowledge-source.yaml) |
| DEC-0344 | `ratified` | Model proxy chain; OpenCodex | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-daemon](../components/qma-daemon.md); [CT-45](../contracts/ct-45-qma-model-deployment-broker.yaml) |
| DEC-0345 | `ratified` | admit / apply / promote split | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Glossary](../glossary.md); [qma-core](../components/qma-core.md) |
| DEC-0346 | `ratified` | Vocabulary and scope reconciliation | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Glossary](../glossary.md); [AGENTS.md](../AGENTS.md) |
| DEC-0347 | `ratified` | Dependency direction (default-deny) | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-core](../components/qma-core.md); [dependencies](../architecture/dependencies.yaml) |
| DEC-0348 | `ratified` | Retired names | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Glossary](../glossary.md) |
| DEC-0349 | `ratified` | Lead Quant (inferred parts Deferred) | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [qma-core](../components/qma-core.md); [Gap report](../gap-report.md), GAP-0071 |
| DEC-0350 | `ratified` | Constitution touchpoints | [ADR-0020](../decisions/ADR-0020-qma-agentic-system.md); [Constitution](../constitution.md); QMA constitution touchpoints (below) |
| DEC-0360 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0361 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0362 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0363 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0364 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0365 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0366 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0367 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0368 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0369 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0370 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0371 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0372 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0373 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0374 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0375 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0376 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0377 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0378 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |
| DEC-0379 | `dead` | Cut (D21) | [Gap report](../gap-report.md), Agentic system (QMA) — dead 20 |

DEC-0300 through DEC-0328 realize the QMA spine AD-1 through AD-29 into `COMP-QMA-CORE`, `COMP-QMA-WIRE` and `COMP-QMA-DAEMON`; DEC-0329 adopts the spine in full and makes the Cut-outright table spine law. DEC-0333 sets the build order and names the first milestone — a Quant reachable through models over the wire — landing in `FEAT-0043`. DEC-0341 and DEC-0327 (AD-16, AD-28) hold the money-path reachability barrier, and DEC-0345 reserves `promote` for the L17 live-zone act performed by a human outside QMA. DEC-0360 through DEC-0379 are minted `status: dead` and recorded in the gap report's **Agentic system (QMA) — dead 20** subsection; `DEC-0084`, `DEC-0085` and `DEC-0086` stay dead independently.

## Gap locator — 80 entries

Every row links the full [gap report](../gap-report.md) and the most direct architecture, component, or contract boundary. The foundation architecture sitting `answered` GAP-0001 through GAP-0015 and GAP-0018 through GAP-0030 (answering DEC named per row) and `deferred` GAP-0016/GAP-0017 to the backtesting sitting; the 2026-08-20 indicators/structure increment `answered` GAP-0031 through GAP-0034 (DEC-0126 through DEC-0129); the 2026-08-20 venue sitting `answered` GAP-0035 through GAP-0038 (DEC-0136, DEC-0137, DEC-0135 + DEC-0139, DEC-0138); the 2026-08-20 risk sitting `answered` GAP-0039 through GAP-0046 (DEC-0143 through DEC-0155). The 2026-08-20/21 QMB increment (DEC-0159 through DEC-0169) partially closed GAP-0048 (fidelity seams ruled, DEC-0164), delivered look-ahead prevention for the deferred GAP-0016/GAP-0017 (spine B-2/B-8/B-12, DEC-0169), and advanced GAP-0049 without closing it. The 2026-08-21 QML increment (DEC-0171 through DEC-0184, child spine QL-1 through QL-10 at `architecture-QML-2026-08-21/`, run autonomously by operator delegation with a 5-lens reviewer gate applied) folded `COMP-QML` — the bot-authoring application-layer library built ON QMF (ADR-0018, `FEAT-0030`) — and `answered` GAP-0047. In total 45 gaps are answered and 0 remain open, with GAP-0016/GAP-0017 (registration gate, DEC-0121), GAP-0048 content, and GAP-0049 deferred. An `answered` row is answered at the ruling level while per-field schema detail may still be documentation-time work; the newly-answered risk gaps now carry `blocking: false` in the catalog, matching the ratified contract surface. GAP-0048 and GAP-0049 name `COMP-QMB` among their consumers in the catalog. The 2026-08-28 trading-node sitting (DEC-0186 through DEC-0260) answered no catalog gap and added eight, GAP-0050 through GAP-0057. The 2026-08-30 documentation-factory veto round (DEC-0261, DEC-0262) then `answered` GAP-0057 (the post-promotion warm-up recollection — no per-bot warm-up on the node, the inherited admission row stands) and raised a ninth node gap GAP-0058 (the placement variants), ruled `open` and IN SCOPE at the second exchange with its design owed by a one-shot architecture increment before the variant's epic (DEC-0262). In total 46 gaps are answered, 0 remain blocking open, the one open non-blocking gap is GAP-0058, and the deferred set is GAP-0016/GAP-0017 (registration gate, DEC-0121), GAP-0048 content, GAP-0049, and the node rows GAP-0050 through GAP-0056, with GAP-0057 now `answered`. GAP-0050 through GAP-0058 name `COMP-QMN` among their consumers; the node touches the deferred backtesting/search gaps only at the admission bar, where a blank bar blocks live regardless (AD-32) and none is node-invented.

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
| GAP-0016 | `deferred` | `false` | Deferred by DEC-0121 to the backtesting sitting; [CT-08](../contracts/ct-08-gate-evidence.yaml). Bitemporal ingredients ratified; look-ahead **prevention** delivered by QMB (spine B-2/B-8/B-12, DEC-0169), only the registration gate stays deferred. Node sitting (2026-08-28) leaves it deferred: touched only at the admission bar (blank bar blocks live, AD-32), the node adds raw material via the evidence tier and four-verdict reconciliation, not policy (DEC-0195, DEC-0208). |
| GAP-0017 | `deferred` | `false` | Deferred by DEC-0121 to the backtesting sitting; [CT-08](../contracts/ct-08-gate-evidence.yaml). QMB makes every trial/replicate/walk-forward window a ledgered run (DEC-0161, DEC-0169), so the counter's raw material is complete; the counting policy stays deferred. Node sitting (2026-08-28) leaves it deferred: the node runs no research campaign and counts no attempts; its do-not-default value roster is node-minted and unrelated to a research budget (DEC-0193). |
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
| GAP-0048 | `deferred` *(partially closed)* | `false` | [Gap report](../gap-report.md); [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md). Seams ruled (DEC-0164): ports, partial fills, lowest-wins, optimistic taint, calibration-not-invention; sandbox/matrix halves answered by the QMB architecture (DEC-0161, DEC-0169). Taxonomy values, calibration content, parity contracts, and simulated-time typing still open. Node sitting (2026-08-28) adds nothing: node replay has no fill simulation, diffing decisions only (DEC-0206); fidelity taint stays QMB tunnel territory and fill simulation in replay is carried as GAP-0056. |
| GAP-0049 | `deferred` | `false` | [Gap report](../gap-report.md); [ADR-0011](../decisions/ADR-0011-deferred-consumer-products.md), [ADR-0017](../decisions/ADR-0017-qmb-experimentation-library.md); [QMB](../components/qmb.md). Raw material accrues by construction (DEC-0161, DEC-0169) plus B-8 anti-overfit sensitivity per sweep; thresholds, SR*, and the staged funnel stay its sitting. Node sitting (2026-08-28) mints no threshold: touched only at the admission bar (blank bar blocks live, AD-32); the node's QA standard gates machinery, not performance (DEC-0208). |
| GAP-0050 | `deferred` | `false` | [Gap report](../gap-report.md), Deferred by the trading-node sitting; [Trading node](../components/trading-node.md), TN-7. KSA trigger→level→effect matrix VALUES: shape closed by TN-7 (DEC-0192), vocabulary re-ratified from the GitBook baseline (DEC-0237); a pre-soak operator ratification through the settings surface, blank/provisional-evidence blocks live (DEC-0231, DEC-0254). Never GAP-0015 (lineage edges, DEC-0114). |
| GAP-0051 | `deferred` | `false` | [Gap report](../gap-report.md), Deferred by the trading-node sitting; [Trading node](../components/trading-node.md), TN-19. MIS labeler training + shadow rollout: a follow-on epic after the paper milestone; TN-19's shadow-lane seam is V1 node work, the models are not (DEC-0204, DEC-0215). |
| GAP-0052 | `deferred` | `false` | [Gap report](../gap-report.md), Deferred by the trading-node sitting; [Trading node](../components/trading-node.md), TN-18. Hot-apply of settings: V1 applies a config change at the next boot epoch; hot-apply is a later mint on the same versioned artifact (DEC-0203, DEC-0223). |
| GAP-0053 | `deferred` | `false` | [Gap report](../gap-report.md), Deferred by the trading-node sitting; [Trading node](../components/trading-node.md), TN-17. The agent/MCP door: a later sibling wrapper over the same library; nothing an agent can reach exists on the node in V1, and the powers channel already refuses every power to the ops principal (DEC-0202, DEC-0234). |
| GAP-0054 | `deferred` | `false` | [Gap report](../gap-report.md), Deferred by the trading-node sitting; [Trading node](../components/trading-node.md), TN-19; [QML](../components/qml.md); [Security model](../lenses/security/security-model.md). Hardened OS-level confinement for seats — QL-8 Layer-2's named deferred dependency; V1 controls named once (callback deadline, memory ceiling, quarantine, restart of last resort), OS confinement not waited on and not closed by V1 seat stories (DEC-0204, DEC-0236, DEC-0260). |
| GAP-0055 | `deferred` | `false` | [Gap report](../gap-report.md), Deferred by the trading-node sitting; [Trading node](../components/trading-node.md), TN-3. A second VPS for the evidence tier: a config change once the placement boundary already exists; the three planes are drawn so co-location is not assumed (DEC-0188, DEC-0201). |
| GAP-0056 | `deferred` | `false` | [Gap report](../gap-report.md), Deferred by the trading-node sitting; [Trading node](../components/trading-node.md), TN-21. Fill simulation in replay: none in V1, replay diffs decisions only (DEC-0206, DEC-0229); fidelity taint stays QMB tunnel territory under GAP-0048. |
| GAP-0057 | `answered` | `false` | [Gap report](../gap-report.md), Deferred by the trading-node sitting; [Trading node](../components/trading-node.md), TN-9/TN-20; [QMF Risk](../components/qmf-risk.md). Post-promotion warm-up recollection surfaced by the SRC-12 transcript scan; `answered` by operator direct ruling at the 2026-08-30 veto round (DEC-0261): NO per-bot warm-up, probation, ramp or paper lane on the node — bots arrive backtested and paper-tested outside the node and operator-approved, the inherited admission row stands, and a bot promoted mid-day does not trade until the next trading day (DEC-0210; R3 DEC-0213). |
| GAP-0058 | `open` | `false` | [Gap report](../gap-report.md), Open gaps — 1 (non-blocking); [Trading node](../components/trading-node.md), TN-3/TN-16/TN-19. Two placement variants IN SCOPE (operator 2026-08-30, DEC-0262): the ratified VPS variant and a single-machine variant co-located with the agentic system as one installed QMX application, the backend setting itself up out of the box. Not a second product — a roster machine-tuple placement change re-scoping the V1 compose-off-tuple refusal (DEC-0188, DEC-0236 ruling 18); design owed (supervision without systemd, secret store without systemd-creds, powers channel without a unix socket, observability placement, self-setup installer) and ruled by a one-shot architecture increment BEFORE the variant's epic, the VPS epics never blocked by it (DEC-0262). |

### Agentic system (QMA) gaps — GAP-0070 through GAP-0091

The QMA sitting deferred 22 questions, all `status: deferred`, `blocking: false`, `answer: null`, each carrying a stated revisit condition. None is revived; the full text is in the [gap report](../gap-report.md), **Deferred by the QMA sitting — 22**. A row is a discussion trigger, not implementation or live-money authority.

| Gap | Status | Blocking | Primary boundary |
|---|---|---:|---|
| GAP-0070 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Windows VPS `desktop` environment, planned not provisioned; every computer-use tool fails `check_fn` until registered (DEC-0336, AD-25). |
| GAP-0071 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md), [qma-daemon](../components/qma-daemon.md). One lead flag per desk and the lead-mailbox catch-all inferred, not ruled; interim rule is a startup error and `dead_letter` (DEC-0349, AD-7/AD-20). |
| GAP-0072 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md), [qma-daemon](../components/qma-daemon.md). External memory backend (Hindsight/Mem0) behind the eval; v1 ships the `MemoryProvider` port and `NoMemoryProvider` only (DEC-0342, AD-18). |
| GAP-0073 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md), [qma-daemon](../components/qma-daemon.md). Knowledge hybrid indexing; v1 is literal and locator search only (DEC-0343, AD-19). |
| GAP-0074 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Self-improvement evaluation gates, gated on the AD-26 finished-Mission trajectory count; v1 ships invariants plus staging (DEC-0321, DEC-0322). |
| GAP-0075 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md), [qma-daemon](../components/qma-daemon.md). Sandbox and compute vendors; Modal, Daytona and E2B rejected outright; backtesting fan-out first (DEC-0316, AD-17). |
| GAP-0076 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). RLM kernel performance envelope; a measurement obligation against the first Analysis fan-out (DEC-0313, AD-14). |
| GAP-0077 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md), [qma-daemon](../components/qma-daemon.md). In-house threading node shape; no contribution type minted until the operator supplies spec or code (DEC-0320, AD-1/AD-21). |
| GAP-0078 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Browser stack; the starting point is reverse-engineering Egolite, not a vendor shortlist (DEC-0315, AD-16/AD-17). |
| GAP-0079 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-wire](../components/qma-wire.md), [qma-daemon](../components/qma-daemon.md). External agent-to-agent transport; the internal bus comes first, the relay/signing transport is itself Cut (DEC-0319, DEC-0368). |
| GAP-0080 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). RLM beyond the Analysis desk and depth above 2; both triggers journal-readable (DEC-0313, AD-14). |
| GAP-0081 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-wire](../components/qma-wire.md). UI presentation, UI SDK and `qma-ui-contract` beyond a stub; the wire contract and variables registry bind now (DEC-0304, DEC-0333). |
| GAP-0082 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Mission reports; revisit after the first missions run (DEC-0338, AD-9). |
| GAP-0083 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md). Desk consolidation, a Profile-level display collapse only; never a `desk_slug`/`ActorId`/scope/index rename (DEC-0306, AD-7). |
| GAP-0084 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md), [qma-daemon](../components/qma-daemon.md). Separate Mission Template registry; after the first three authored graph packs (DEC-0340, AD-13). |
| GAP-0085 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md). Typed strategy-mechanism decomposition; QML and `qmf-registry` own strategy semantics, revisit at the QML sitting (DEC-0313, AD-14). |
| GAP-0086 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Graph engine implementation; when the first three authored graph packs exist (DEC-0312, AD-13). |
| GAP-0087 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Claude Agent SDK hook count 7-vs-10; bounded by the Cut on foreign runtimes, nothing in the spine depends on it (DEC-0309, DEC-0360). |
| GAP-0088 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Backup destination, encryption-key custody and restore cadences; decided at first durable-store open, registered under AD-26 (DEC-0326, AD-27). |
| GAP-0089 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Trim window for the bounded non-evidence streams; the AD-6 event journal is never trimmed (DEC-0319, DEC-0322). |
| GAP-0090 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-daemon](../components/qma-daemon.md). Context compaction rule; until the ceiling is reached, compaction persists nothing and no compacted transcript is evidence (DEC-0313, AD-14). |
| GAP-0091 | `deferred` | `false` | [Gap report](../gap-report.md); [qma-core](../components/qma-core.md), [qma-wire](../components/qma-wire.md), [qma-daemon](../components/qma-daemon.md). Interactive walkthrough artifact; an optional operator aid, revisit after review. |

## Feature locator — 38 entries

Waves are the derived dependency waves from `_docwork/feature_inventory.yaml`. The blocker summaries preserve the dependency edges but replace stale wording with the current venue contract topology; they do not declare any blocker complete, and the venue contracts being filled at version 1 does not lift the corpus-wide provisional gate or grant implementation authority. `FEAT-0028` (forex market-hours calendar extension) and `FEAT-0029` (QMB experimentation library and `qmb` CLI) join the inventory; `FEAT-0029` is the QMB increment's headline feature and carries its own gate below. `FEAT-0030` (QML bot-authoring library) joins as the QML increment's headline feature, blocked only on the qmf-core, qmf-registry, and qmf-risk contract surfaces it imports — never on `FEAT-0029` or any node feature (DEC-0180). `FEAT-0031` (the trading node, `qmn`) joins as the trading-node increment's headline feature — a multi-pass supervised composition-root runtime, one product with two modes `paper | live`, built ON QMF and the sole sanctioned wirer of `qmf-venue`; it depends on the venue, risk, QMB and QML contract surfaces plus the journal, backup and data adapters it executes, and carries its own scope and gate below (DEC-0186, DEC-0259).

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
| FEAT-0031 | 15 | [COMP-QMN](../components/trading-node.md) | `planned` | FEAT-0023 (the CT-18–CT-21 shapes the node-minted `VenueClientPort` is built over, whose conformance double is the port's third implementation), FEAT-0024/FEAT-0025/FEAT-0026 (the cTrader session, market-data and order/reconciliation adapters the transport increment completes inside qmf-venue's ConnectionManager, A37), FEAT-0027 (the CT-22/23/24/25/27/28/29/30/31/32 Book/BMS/risk contracts and the AD-40 dimensional law the node runs VERBATIM), FEAT-0028 (the forex market-hours calendar identity the node registers at composition), FEAT-0029 (QMB's `run_slice` loop driven unforked behind the accumulator, the config compiler, and the passive-hub registry-read port), FEAT-0030 (the QL-7 runtime protocol, conformance gate and prediction linter `seats/` hosts), and FEAT-0012/FEAT-0013/FEAT-0014/FEAT-0016/FEAT-0017 (the CT-13 journal-evidence, backup, raw-observation, journal-persistence and off-machine restore adapters the node executes). The node is an application layer built ON QMF and the sole sanctioned wirer of `qmf-venue`; nothing imports `qmn`, and it adds no QMF package edge (DEC-0186). Ratified by operator delegation plus four direct rulings (spine TN-1..TN-25 FINAL, DEC-0259). Detailed gate below. |

### Agentic system (QMA) features — FEAT-0040 through FEAT-0046

The QMA increment adds seven implementing features in the operator's build order (`SRC-15`): `FEAT-0040` through `FEAT-0046`, all `size: multi-pass`, `status: planned`. The Wave column carries the QMA build-order step; the derived dependency wave sits on the QMF roster features each consumes. The QMX agentic system is an application-layer consumer built ON QMF — every edge carries a reason and no feature adds a QMF package edge or reverses a dependency direction. The first milestone, a Quant reachable through models over the wire, lands in `FEAT-0043`. Ratified by operator delegation via the rider; implementation ships only through the factory pipeline.

| Feature | Wave | Component | Status | Blocker summary |
|---|---:|---|---|---|
| FEAT-0040 | 1 | [COMP-QMA-CORE](../components/qma-core.md) | `planned` | FEAT-0005 (qmf-core substrate). The definitions package: ontology, the seven ports, the plugin contribution surface and the QMA refusal variants; depends only on qmf-core (DEC-0300, DEC-0335, DEC-0337, DEC-0347). |
| FEAT-0041 | 2 | [COMP-QMA-WIRE](../components/qma-wire.md) | `planned` | FEAT-0040. The wire envelope, the command/query/event families and JSON-Schema message families, `protocolVersion` and the transport posture (DEC-0304, DEC-0303, DEC-0336). |
| FEAT-0042 | 3 | [COMP-QMA-CORE](../components/qma-core.md), [COMP-QMA-DAEMON](../components/qma-daemon.md) | `planned` | FEAT-0040, FEAT-0041. The daemon substrate: one journal / sole writer / clock, the closed store list, the hooks registry, the Task Graph and store lifecycle (DEC-0305, DEC-0334, DEC-0338, DEC-0339, DEC-0340). |
| FEAT-0043 | 4 | [COMP-QMA-CORE](../components/qma-core.md), [COMP-QMA-DAEMON](../components/qma-daemon.md) | `planned` | FEAT-0042, FEAT-0007 (qmf-registry read-and-calculate), FEAT-0027 (qmf-risk read-and-calculate). The model proxy, Tool Registry, permissions and Credential Broker, and the money-path reachability barrier; the first milestone lands here (DEC-0314, DEC-0323, DEC-0341, DEC-0344). |
| FEAT-0044 | 5 | [COMP-QMA-CORE](../components/qma-core.md), [COMP-QMA-DAEMON](../components/qma-daemon.md) | `planned` | FEAT-0043, FEAT-0029 (QMB). Execution environments, the Compute Router, JobHandle, the RLM kernel and the QMB door (ExperimentSpec) (DEC-0316, DEC-0324, DEC-0313). |
| FEAT-0045 | 6 | [COMP-QMA-CORE](../components/qma-core.md), [COMP-QMA-DAEMON](../components/qma-daemon.md) | `planned` | FEAT-0042. The three ledgers, the Agent Bus, the scheduler and Routines, the memory and knowledge ports, the admission gate and telemetry export (DEC-0308, DEC-0317, DEC-0318, DEC-0319, DEC-0321, DEC-0322, DEC-0328, DEC-0342, DEC-0343, DEC-0345). |
| FEAT-0046 | 7 | [COMP-QMA-CORE](../components/qma-core.md), [COMP-QMA-DAEMON](../components/qma-daemon.md) | `planned` | FEAT-0043, FEAT-0044, FEAT-0045. The plugin loader with reversible scopes and the five desk plugin packs; the loader is daemon-owned and the contribution surface is [qma-core](../components/qma-core.md) (DEC-0320, DEC-0300). |

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

## FEAT-0031 scope and gate

FEAT-0031 is the trading node (`qmn`) — the implementing feature for `COMP-QMN`, ratified at the planning level by the 2026-08-28 trading-node sitting (child spine TN-1 through TN-25 FINAL, ADR-0019, DEC-0186 through DEC-0260, adopted in full by DEC-0259). It is a multi-pass feature: ONE product with two modes `paper | live`, a supervised composition-root runtime over a pure rulebook, a top-level uv-workspace member built ON QMF exactly as QMB and QML are, and the sole sanctioned importer and wirer of `qmf-venue` at its `qmn.venue` boundary (DEC-0186, DEC-0241). It covers building the ratified TN-1 through TN-25 spine across the structural seed (`host/`, `loop/`, `venue/`, `orderpath/`, `protection/`, `ledger/`, `paper/`, `reconcile/`, `seats/`, `promotion/`, `mis/`, `data/`, `time/`, `secrets/`, `config/`, `observability/`, `doors/`, `replay/`, `bench/`, `deploy/`), the operations toolkit of `just node-…` recipes, and the node's half of the separate zero-authority observability stack. It authorizes no order, no credential use, no live-money action, no promotion, and no destructive act; implementation and every such authority arrive only through the factory pipeline. The node runs the Book/BMS/risk contracts VERBATIM and adds no rule of its own — the chain of command is wired, not redefined (DEC-0191, DEC-0193).

### Ratified inputs the implementation consumes

- The live loop IS QMB's `run_slice` loop driven UNFORKED behind a push-to-pull accumulator that is the single first writer, one loop instance per command stream, with the interpretation cursor kept apart from the receive frontier (DEC-0190); the composition root composes → fingerprints → seals a `composition_fp` and records a boot-attempt, with preflight and a check mode (DEC-0187). One asyncio loop at the edge, systemd supervision, stand-down-alive with the operator `resurrect` as its only exit, and a shutdown contract that mints UNKNOWN for in-flight commands and never flattens (DEC-0189, DEC-0218, DEC-0226).
- The order path is the AD-36/AD-37 chain of command wired with veto and suppression paths named apart, entry-side-only blocks that preserve every exit (L39), collapse/conflict/compose, the command ordinal kept apart from the journal sequence, durable command-id binding, and a submission deadline from wire handoff (DEC-0191, DEC-0221, DEC-0224). KSA is the protection authority — five fixed levels and four addable trigger classes adopted from the GitBook baseline, escalate-only automatic transitions with human-only de-escalation, a monotone fold, the effect matrix as node severity policy, the kill switch under a dead wire, and never-auto predicates (DEC-0192, DEC-0237); the risk protection set runs verbatim — the kill line that IS AD-40's `loss_floor` evaluated per binding against that binding's virtual-ledger equity series, the control windows, SQS reaching the door only inside the signal snapshot with its baseline keyed by environment, the breakeven ratchet, and the bench fold (DEC-0193, DEC-0216, DEC-0230, DEC-0255).
- The node mints `VenueClientPort` over the CT-18 through CT-21 shapes; the cTrader transport increment lands inside qmf-venue's ConnectionManager as the one delegated impurity (A37), with rotation scoped by credential reference, exact scaled-integer equity derivation at the account money exponent, and `netting | hedging` measured at bind time and honoured at dispatch (DEC-0196, DEC-0219, DEC-0222, DEC-0228). Secrets are a two-layer store with three named holders, a provisioning wizard over SSH stdin, and backup payload-key custody escrowed on the workstation with an offline copy (DEC-0197, DEC-0227, DEC-0252).
- Startup, recovery and explained-drift doctrine with FOUR reconciliation verdicts, `resolve_unknown` on two declared paths — automatic from an unambiguous read-back inside the lookback, operator attestation through the powers channel otherwise, drift stand-down keyed by role, and `operator_review` (DEC-0195, DEC-0258); the accounting boundary and virtual ledger — the account-scoped day-boundary calendar identity declared and never inferred, the virtual (Book) position fold named apart from the venue position, operator-signed journaled treasury boundary acts that never touch positions, and mandatory per-counter `state_carry` (DEC-0210, DEC-0225, DEC-0251). Every node-minted variable is configurable, unit-kinded, owner-scoped and blank-effect tagged, carrying a value-status (blank | provisional-evidence | ratified) countersigned through the powers channel (DEC-0256, DEC-0254, DEC-0231).

### Topology the implementation must preserve

- `COMP-QMN` is backend runtime in `docs/architecture/dependencies.yaml`, depending on `qmf.*` (including qmf-venue), qmb, qml and the extensions; NOTHING imports `qmn`. The node adds no QMF package edge and reverses no dependency direction — it is an application layer built ON QMF, never a `qmf.*` roster package and never a framework (DEC-0186).
- The node is the sole sanctioned wirer of `qmf-venue`: L30 is annotated at source so `qmn.venue` is the sanctioned qmf-venue import boundary (DEC-0241), and the QMF async-conformance test is amended to exempt `qmf.venue.connection` by name as a declared exemption — the one delegated impurity — with its refusal path pre-ruled (the transport increment moves into `qmn.venue.ctrader`) so no epic must choose (DEC-0243). The candidate parent amendment to realize `VenueClientPort` inside qmf-venue is recorded-not-applied; a child never amends a parent by assertion (DEC-0242).
- The three doors are the in-process Python API, the localhost HTTP evidence channel (publish-never-act, per-read provenance fields), and the unix-socket powers channel under SO_PEERCRED with two declared principals and a closed powers list; there is NO operator command line — the operations toolkit of `just node-…` recipes is DevOps tooling, never a trading control (DEC-0202, DEC-0211, DEC-0234). Config is ONE resolved, fingerprinted node-config artifact compiled from four explicit layers with no invocation layer, carrying eligibility and identity only while runtime state stays a read-time fold; extensibility is registry plus config plus a restart at a safe point, never code (DEC-0203, DEC-0223).

### Entry and exit gate

FEAT-0031's blockers are ordering constraints, not proof any seam is wired: FEAT-0023 through FEAT-0026 (the venue port shapes and the cTrader transport increment), FEAT-0027 (the Book/BMS/risk contracts run verbatim), FEAT-0028 (the forex market-hours calendar identity), FEAT-0029 (QMB's loop, config compiler and hub), FEAT-0030 (the QL-7 runtime protocol and conformance gate), and FEAT-0012/FEAT-0013/FEAT-0014/FEAT-0016/FEAT-0017 (the journal-evidence, backup, raw-observation, journal-persistence and off-machine restore adapters). Its exit conditions are implementation-shaped and gate on the SOAK: the soak acceptance checklist — the FULL first-deploy warm-up week, unattended, on the demo binding, each item journaled and each carrying an injected-fault drill where applicable — PASSES (DEC-0194, DEC-0208, DEC-0212); the live binding then satisfies its OWN baselines (a live-conditioned SQS baseline and a live-path rung baseline present on this deployment tuple, minted from the sensing-and-recording-only live connection) so the bind-time check passes rather than being waived (DEC-0230); the four risk golden scenarios SCN-0006, SCN-0008, SCN-0010 and SCN-0011 are wired and proven by the node that wires them; the gated `FAILURES.md` register generates the alert allow-list; and the permanent battery, the requirements-first `qa/` tests, the one venue conformance suite (proving the port against both the FEAT-0023 conformance double and the live cTrader client) and nightly mutmut over the node's money-path modules are green on the branch that carries code (DEC-0208, DEC-0228). The QA-debt rows discharged here are node stories BY NAME, each citing its id — QMX-F045, F046, F062, F063, F064, F067, F068, F069, F102, D008, D010, E15-F01/F02/F03, E7-R28, E9-F04, and E12-F01/F04/F05 — and foundation debt stays foundation, NOT in this feature (DEC-0208). Until the factory builds and authorizes it, `COMP-QMN` remains non-buildable outside the pipeline; the node epics branch from origin/integration @ ef9bb25 (never the stale local ref) and land back through the factory lane, and human-only promotion with a separate activation act remains absolute (DEC-0186, DEC-0205, DEC-0213). Open after this feature: the KSA matrix VALUES (GAP-0050, a pre-soak operator ratification), GAP-0016/GAP-0017 and GAP-0048/GAP-0049 (all four blank-bar-blocks-live at the admission bar, never node-invented), the six node deferred rows GAP-0051 through GAP-0056, and GAP-0058 (the placement variants, `open` and in scope, design owed by a one-shot architecture increment before the variant's epic, DEC-0262); GAP-0057 (the per-bot warm-up recollection) is answered (DEC-0261).

## QMA constitution touchpoints

The QMX agentic system binds ten parent constitution laws read-only; QMA amends no parent by assertion, and these rows are the recorded touchpoints (`DEC-0350`). Each names the AD through which the law reaches QMA. The parent conventions rows of the Inherited Invariants table also bind read-only.

| Constitution law | Binds QMA via | Reading |
|---|---|---|
| **L17** — human-gated promotion | AD-24, AD-25 | Promotion into the live zone is a human act outside QMA; QMA mints no promotion or zone-transition command and records only the resulting artifact ref (DEC-0345, DEC-0323). |
| **L18** — store lifecycle discipline | AD-27 | Store versioning, migration (preflight, backup-first, dry-run, migrate, verify) and backup/restore follow the parent's AD-20 / L18 order (DEC-0326). |
| **L30** — roster scope (annotation) | AD-2 | The 2026-08-21 L30 roster-scope annotation places QMA's `qmf-registry` and `qmf-risk` read-and-calculate edges as application dependencies under L31 (DEC-0347). |
| **L31** — built with QMF, no contract re-implemented | AD-4 | L31 is dispositive for one Python 3.14 asyncio daemon built with QMF — no second daemon runtime, no contract re-implemented across a language boundary (DEC-0334). |
| **L33** — plain-Python escape hatch | AD-14 | `StrategyHandle` may create only content-addressed candidate artifacts in the parent registry's existing `dev` zone, mutating nothing (DEC-0313). |
| **L34** — secrets are references, never values | AD-24 | Components handle credential references only; values resolve inside the Credential Broker's egress call frame from the OS secret store (DEC-0323). |
| **L35** — adopted (UNKNOWN blocks its stream) | AD-12, AD-17 | An LLM may propose a transition but never author a terminal outcome, and an `unknown` job or Task holds its lease until an explicit recorded resolution (DEC-0311, DEC-0316). |
| **L36** — nothing above a bot on the market | AD-16, AD-28 | No execution tool exists at any account role, paper included, and the reachability barrier refuses any environment or edge that could reach the trading node (DEC-0341, DEC-0327). |
| **L38** — configurable means UI-editable | AD-26 | Every AD-26 variable declares `configurable: true` (UI-editable) or `false` (uneditable), carried in the variables registry (DEC-0325). |
| **L39** — exit-preservation / evidence recording | AD-5, AD-6, AD-9, AD-10, AD-21, AD-25, Conventions | L39 is discharged in six places plus Conventions: an evidence append arriving without a `correlation_id` is recorded under a daemon-minted lifecycle id annotated `correlation_missing` rather than refused (DEC-0304); the event journal is never trimmed (DEC-0305); the ledger quarantine path writes a refused entry verbatim and never discards it (DEC-0308); `before_ledger_append` fails open, so no permission policy or precedence resolution refuses a well-formed evidence append from the lease holder (DEC-0309); the load-refusal law never terminates a running daemon or discards a pending evidence append (DEC-0320); and the live boundary keeps L39 with the node, so nothing in QMA may invert, shortcut or automate it (DEC-0324). |
