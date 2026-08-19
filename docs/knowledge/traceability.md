---
id: KNOW-TRACEABILITY-QMF-V1
title: QMF V1 Decision, Gap, and Feature Traceability
type: knowledge
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0001, DEC-0003, DEC-0004, DEC-0024]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _docwork/feature_inventory.yaml, docs/architecture/dependencies.yaml, docs/]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF V1 Decision, Gap, and Feature Traceability

This docs-local locator covers every ledger decision (`DEC-0001` through `DEC-0098`), gap (`GAP-0001` through `GAP-0049`), and inventory feature (`FEAT-0001` through `FEAT-0027`). Statuses are copied from the provisional ledger, gap catalog, and feature inventory; a locator is not ratification or implementation permission. Recommendations remain non-authorizing evidence, and no row grants credential, external-connection, order, promotion, live-money, restore, deletion, or destructive authority. [DEC-0001] [DEC-0003] [DEC-0004]

## Decision locator — 98 entries

The locator names the primary docs-local document and section. `dead`, `superseded`, `conflict`, `open`, and `out-of-scope` statuses are preserved so later agents do not revive or silently settle them.

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
| DEC-0032 | `open` | [ADR-0003](../decisions/ADR-0003-definitions-only-core.md), Consequences |
| DEC-0033 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0034 | `dead` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Options considered |
| DEC-0035 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0036 | `open` | [Gap report](../gap-report.md), Open ledger decisions |
| DEC-0037 | `dead` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Options considered |
| DEC-0038 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0039 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0040 | `conflict` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Consequences |
| DEC-0041 | `provisional` | [ADR-0004](../decisions/ADR-0004-registry-identity-lineage.md), Decision |
| DEC-0042 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0043 | `open` | [Gap report](../gap-report.md), Open ledger decisions |
| DEC-0044 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0045 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0046 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0047 | `open` | [Gap report](../gap-report.md), Open ledger decisions |
| DEC-0048 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0049 | `open` | [Gap report](../gap-report.md), Open ledger decisions |
| DEC-0050 | `superseded` | [Gap report](../gap-report.md), Redesigned or superseded |
| DEC-0051 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0052 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0053 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0054 | `provisional` | [ADR-0005](../decisions/ADR-0005-governed-data-evidence.md), Decision |
| DEC-0055 | `provisional` | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md), Decision |
| DEC-0056 | `provisional` | [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md), Decision |
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

## Gap locator — 49 entries

Every row links the full [gap report](../gap-report.md) and the most direct architecture, component, or contract boundary. `blocking: false` does not turn a recommendation into an answer.

| Gap | Status | Blocking | Primary boundary |
|---|---|---:|---|
| GAP-0001 | `open` | `true` | [Gap report](../gap-report.md); [stack](../architecture/stack.md), runtime matrix |
| GAP-0002 | `open` | `true` | [Gap report](../gap-report.md); [dependencies](../architecture/dependencies.yaml), component packaging |
| GAP-0003 | `open` | `true` | [Gap report](../gap-report.md); [stack](../architecture/stack.md), build and package tooling |
| GAP-0004 | `open` | `true` | [Gap report](../gap-report.md); [stack](../architecture/stack.md), pipeline tiers |
| GAP-0005 | `open` | `true` | [Gap report](../gap-report.md); [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| GAP-0006 | `open` | `true` | [Gap report](../gap-report.md); [stack](../architecture/stack.md), dependency policy |
| GAP-0007 | `open` | `true` | [Gap report](../gap-report.md); [CT-01](../contracts/ct-01-money-quantity.yaml) |
| GAP-0008 | `open` | `true` | [Gap report](../gap-report.md); [CT-02](../contracts/ct-02-time-calendar.yaml) |
| GAP-0009 | `open` | `true` | [Gap report](../gap-report.md); [CT-03](../contracts/ct-03-instrument-identity.yaml) |
| GAP-0010 | `open` | `true` | [Gap report](../gap-report.md); [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| GAP-0011 | `open` | `true` | [Gap report](../gap-report.md); [CT-04](../contracts/ct-04-typed-refusal.yaml) |
| GAP-0012 | `open` | `true` | [Gap report](../gap-report.md); [CT-05](../contracts/ct-05-version-fingerprint.yaml) |
| GAP-0013 | `open` | `true` | [Gap report](../gap-report.md); [performance budgets](../lenses/performance/budgets.md) |
| GAP-0014 | `open` | `true` | [Gap report](../gap-report.md); [CT-06](../contracts/ct-06-registration.yaml) |
| GAP-0015 | `open` | `true` | [Gap report](../gap-report.md); [CT-07](../contracts/ct-07-lineage-edge.yaml) |
| GAP-0016 | `open` | `true` | [Gap report](../gap-report.md); [CT-08](../contracts/ct-08-gate-evidence.yaml) |
| GAP-0017 | `open` | `true` | [Gap report](../gap-report.md); [CT-08](../contracts/ct-08-gate-evidence.yaml) |
| GAP-0018 | `open` | `true` | [Gap report](../gap-report.md); [CT-22](../contracts/ct-22-book-charter.yaml) |
| GAP-0019 | `open` | `true` | [Gap report](../gap-report.md); [CT-06](../contracts/ct-06-registration.yaml) |
| GAP-0020 | `open` | `true` | [Gap report](../gap-report.md); [qmf-data](../components/qmf-data.md), interfaces and behavior |
| GAP-0021 | `open` | `true` | [Gap report](../gap-report.md); [CT-09](../contracts/ct-09-registry-persistence.yaml) |
| GAP-0022 | `open` | `true` | [Gap report](../gap-report.md); [qmf-data store](../components/qmf-data-store.md), failure modes |
| GAP-0023 | `open` | `true` | [Gap report](../gap-report.md); [CT-10](../contracts/ct-10-source-observation.yaml) |
| GAP-0024 | `open` | `true` | [Gap report](../gap-report.md); [CT-12](../contracts/ct-12-dataset-split.yaml) |
| GAP-0025 | `open` | `true` | [Gap report](../gap-report.md); [CT-13](../contracts/ct-13-journal.yaml) |
| GAP-0026 | `open` | `true` | [Gap report](../gap-report.md); [CT-11](../contracts/ct-11-evidence-persistence.yaml) |
| GAP-0027 | `open` | `true` | [Gap report](../gap-report.md); [CT-14](../contracts/ct-14-backup-restore.yaml) |
| GAP-0028 | `open` | `true` | [Gap report](../gap-report.md); [data ingest](../components/qmf-data-ingest.md), authority boundary |
| GAP-0029 | `open` | `true` | [Gap report](../gap-report.md); [CT-15](../contracts/ct-15-external-source-adapter.yaml) |
| GAP-0030 | `open` | `true` | [Gap report](../gap-report.md); [CT-10](../contracts/ct-10-source-observation.yaml) |
| GAP-0031 | `open` | `true` | [Gap report](../gap-report.md); [CT-16](../contracts/ct-16-indicator.yaml) |
| GAP-0032 | `open` | `true` | [Gap report](../gap-report.md); [CT-16](../contracts/ct-16-indicator.yaml) |
| GAP-0033 | `open` | `false` | [Gap report](../gap-report.md); [CT-16](../contracts/ct-16-indicator.yaml) |
| GAP-0034 | `open` | `true` | [Gap report](../gap-report.md); [CT-17](../contracts/ct-17-causal-structure.yaml) |
| GAP-0035 | `open` | `true` | [Gap report](../gap-report.md); [CT-21](../contracts/ct-21-venue-secret-session.yaml) |
| GAP-0036 | `open` | `true` | [Gap report](../gap-report.md); [CT-19](../contracts/ct-19-venue-command.yaml) and [CT-20](../contracts/ct-20-venue-event.yaml) |
| GAP-0037 | `open` | `true` | [Gap report](../gap-report.md); [CT-18](../contracts/ct-18-venue-capabilities.yaml) |
| GAP-0038 | `open` | `true` | [Gap report](../gap-report.md); [CT-18](../contracts/ct-18-venue-capabilities.yaml) |
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

Waves are the derived dependency waves from `_docwork/feature_inventory.yaml`. The blocker summaries preserve the dependency edges but replace stale wording with the current reserved contract topology; they do not declare any blocker complete.

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
| FEAT-0023 | 9 | [COMP-QMF-VENUE](../components/qmf-venue.md) | `planned` | FEAT-0012: CT-13 evidence boundary; CT-18 through CT-21 remain reserved, and CT-19 caller/authorization evidence remains GAP-0036/GAP-0039. |
| FEAT-0024 | 10 | [COMP-QMF-VENUE](../components/qmf-venue.md) | `planned` | FEAT-0023: reserved venue capabilities/session shapes; every credential-bearing operation remains blocked by GAP-0035. |
| FEAT-0025 | 13 | [COMP-QMF-VENUE](../components/qmf-venue.md) | `planned` | FEAT-0024 and FEAT-0016: session plus data-persistence boundaries; venue observations may enter qmf-data through CT-10 only after ratification. |
| FEAT-0026 | 14 | [COMP-QMF-VENUE](../components/qmf-venue.md) | `planned` | FEAT-0025: session, instrument, time, and evidence boundaries; uncertain submission blocks implementation under GAP-0036. |
| FEAT-0027 | 10 | [COMP-QMF-RISK](../components/qmf-risk.md) | `planned` | FEAT-0023: reserved venue seam; detailed fenced gate below. |

## FEAT-0027 fenced scope and gate

FEAT-0027 is a documentation and reconciliation pass, not a risk implementation pass. It authorizes no Book/BMS runtime, risk decision, exit, order authorization, venue call, account transition, credential use, live-money action, journal handoff, or store write.

### Inputs that must remain unresolved until ruled

- DEC-0040 remains `conflict` on Bot-to-confluence cardinality, and GAP-0018 blocks the Bot/Book binding schema.
- DEC-0067 remains `conflict` on exit ownership, and GAP-0040 blocks any exit routing or policy implementation.
- DEC-0069 is `dead`: parallel Bot paper twins must not be revived. DEC-0070 remains provisional study-recap evidence because the direct operator wording is missing; CT-24 is evidence-only until explicit operator confirmation and GAP-0041.
- GAP-0039 through GAP-0046 block Book/BMS schemas, ownership, modes, news control, SQS, formulas, stop-out/benchmark language, and same-tick priority. Recommendations for those gaps remain discussion prompts, not answers.
- The meaning of R stays referenced through `registry:original_risk_unit`; the feature must not restate the registry value or revive dead FORM-0006, DPR, PRS, or legacy capital-slot machinery.

### Topology that the reconciliation must preserve

- Downstream QMF components consume CT-10 from `COMP-QMF-DATA`; `COMP-QMF-DATA-INGEST` and `COMP-QMF-VENUE` may produce CT-10 into Data, but downstream components never depend on Data-Ingest.
- CT-18 and CT-20 have no active QMF V1 downstream consumers. Their listed Data/Risk consumers are intended only, pending GAP-0036/GAP-0038.
- CT-19 is a reserved transport shape for an eventual out-of-scope QMX application. Its caller, authorization producer, and authorization evidence remain unassigned under GAP-0036/GAP-0039; no live command is buildable.
- CT-21 is a no-operation gate: no credential-bearing integration proceeds until GAP-0035 is ratified.
- CT-22 through CT-25 are reserved and unwired. CT-23 has no caller, CT-24 remains evidence-only pending confirmation and GAP-0041, and CT-25 is not wired to `COMP-QMF-DATA`.

### Entry and exit gate

The inventory edge from FEAT-0023 remains an ordering constraint, not proof that the venue seam is complete. FEAT-0027 may enter drafting only after the reserved venue shapes and their unresolved authority boundary are carried forward without invented active wiring.

FEAT-0027 exits only when the operator explicitly rules on DEC-0040, DEC-0067, the DEC-0070 evidence caveat, and every inventory blocker: GAP-0002, GAP-0003, GAP-0004, GAP-0005, GAP-0007, GAP-0008, GAP-0011, GAP-0013, GAP-0018, GAP-0019, GAP-0025, GAP-0036, and GAP-0039 through GAP-0046. The resulting Book/BMS, caller, consumer, state-transition, formula, evidence, and failure contracts must be ratified, and dependency plus registry artifacts must be updated through the documentation change protocol. Until that gate passes, `COMP-QMF-RISK` remains non-buildable, all CT-22 through CT-25 handoffs remain inactive, and human-only promotion remains absolute.
