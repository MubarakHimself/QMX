---
id: DOC-INDEX
title: QMF V1 Documentation Index
type: index
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0001, DEC-0003, DEC-0004, DEC-0024, DEC-0100, DEC-0106, DEC-0120, DEC-0122, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0134, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0140, DEC-0141, DEC-0142]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _docwork/feature_inventory.yaml, docs/architecture/dependencies.yaml, docs/, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF V1 Documentation Index

This is the docs-only front door to the QMF V1 knowledge base. All artifacts remain `provisional`: they authorize no implementation, credential use, external connection, order, live-money action, promotion, restore, deletion, or other destructive operation. Research and recommendations remain evidence for a later operator ruling, never automatic adoption. [DEC-0001] [DEC-0003] [DEC-0004]

The corpus contains 88 files: 60 Markdown documents and 28 YAML artifacts. Every file is linked once below and grouped by the project taxonomy. The 2026-08-19/20 foundation architecture sitting (spine AD-1 through AD-21, ledger DEC-0099 through DEC-0125) added ADR-0012 through ADR-0016 and the first market-hours calendar extension spec; the 2026-08-20 indicators/structure increment (spine AD-22 through AD-25, ledger DEC-0126 through DEC-0134) ratified the CT-16 two-mode indicator protocol and series vocabulary, the canonical TA-Lib 0.7.1 arithmetic pin, the light/heavy four-bound rule, and the CT-17 causal structure lifecycle, absorbed in ADR-0006; the 2026-08-20 venue architecture sitting (spine AD-26 through AD-28, ledger DEC-0135 through DEC-0142) ratified the venue secret lifecycle, the four-command uncertainty law, and the one-port four-contract adapter, filling CT-18 through CT-21 and rewritten into ADR-0007. Their rationale is absorbed across the architecture-decision set below.

## Start here and governance

- [Documentation index](index.md) — maps every file in the docs-local knowledge base.
- [Agent entry point](AGENTS.md) — gives coding agents the reading order, hard laws, architecture preflight, and change protocol.
- [Constitution](constitution.md) — states the project-wide laws that every component and future implementation must obey.
- [Glossary](glossary.md) — provides the canonical project vocabulary and rejected aliases.
- [Gap report](gap-report.md) — catalogs the answered, open, deferred, conflict, dead, and out-of-scope decision surfaces; the sittings answered 36 gaps, 8 remain open (GAP-0039–GAP-0046, the risk sitting), and 5 are deferred.
- [Traceability locator](knowledge/traceability.md) — locates every DEC, GAP, and FEAT ID in the docs-local corpus.
- [Changelog](changelog.md) — records creation of the provisional knowledge base and future documentation changes.

## Architecture

- [Architecture overview](architecture/overview.md) — presents the C4 context, containers, layers, component topology, and reserved seams.
- [Stack and delivery surface](architecture/stack.md) — records adopted and unresolved runtime, package, store, toolchain, and CI choices by layer.
- [Dependency manifest](architecture/dependencies.yaml) — provides the machine-readable component graph, layers, interfaces, and spec paths, including the default-deny dependency direction and the one ratified inter-library edge (DEC-0120).

## Registry

- [Variables registry](registry/variables.yaml) — is the machine-readable source of truth for values, symbols, thresholds, and unresolved value gaps.

## Components

- [qmf-core](components/qmf-core.md) — specifies the definitions-only, asset-neutral foundation values and refusal/version boundaries.
- [qmf-registry](components/qmf-registry.md) — specifies identity, lineage, registration, causality-gate, attempt, and promotion boundaries.
- [qmf-data](components/qmf-data.md) — specifies governed bitemporal evidence, dataset, journal, and data-access boundaries.
- [qmf-indicators](components/qmf-indicators.md) — specifies the package-neutral two-mode indicator protocol, series vocabulary, and TA-Lib wrapper boundary.
- [qmf-structure](components/qmf-structure.md) — specifies QMX-owned causal level, zone, and market-structure evidence.
- [QMF Venue](components/qmf-venue.md) — specifies the ratified venue-neutral adapter module: the secret lifecycle, four-command uncertainty law, and one-port four-contract adapter, with authorization still only through the factory pipeline (DEC-0136, DEC-0137, DEC-0138).
- [QMF Risk](components/qmf-risk.md) — fences Book, BMS, risk, mode, and journal placeholders pending FEAT-0027 reconciliation.
- [qmf-data ingest seam](components/qmf-data-ingest.md) — specifies the active CT-15 source boundary and CT-10 production into qmf-data.
- [qmf-data store](components/qmf-data-store.md) — specifies the unresolved physical persistence adapter boundary.
- [qmf-data backup](components/qmf-data-backup.md) — specifies ownership of the reserved CT-14 backup/restore evidence boundary.
- [qmf-calendar-forex](components/qmf-calendar-forex.md) — specifies the first market-hours calendar extension: a package outside the roster on its own SemVer ladder implementing the CT-02 calendar-provider protocol for forex.
- [cTrader Open API](components/ctrader.md) — records the external cTrader authority boundary and unwired venue shapes.
- [Dukascopy](components/dukascopy.md) — records the external historical-source boundary for bounded acquisition.
- [Economic-calendar feed](components/calendar-feed.md) — records the external provider boundary for the standalone recorder.
- [Off-machine object storage](components/object-storage.md) — records the unresolved external destination for future backup objects.

## Contracts

- [CT-01 — money and quantity](contracts/ct-01-money-quantity.yaml) — reserves exact money, price, and quantity value semantics.
- [CT-02 — time and calendar rule sets](contracts/ct-02-time-calendar.yaml) — reserves exact instants, trading dates, sessions, and calendar rule sets.
- [CT-03 — instrument identity](contracts/ct-03-instrument-identity.yaml) — reserves asset-neutral instrument and venue identity.
- [CT-04 — typed refusal](contracts/ct-04-typed-refusal.yaml) — reserves the shared public refusal envelope.
- [CT-05 — version and fingerprint](contracts/ct-05-version-fingerprint.yaml) — reserves canonical serialization, fingerprint, and compatibility values.
- [CT-06 — registration](contracts/ct-06-registration.yaml) — reserves registry registration and promotion evidence.
- [CT-07 — lineage edge](contracts/ct-07-lineage-edge.yaml) — reserves typed provenance and amendment relationships.
- [CT-08 — gate evidence](contracts/ct-08-gate-evidence.yaml) — reserves causality, look-ahead, and attempt-gate evidence.
- [CT-09 — registry persistence](contracts/ct-09-registry-persistence.yaml) — reserves registry persistence through the data-store seam.
- [CT-10 — source observation](contracts/ct-10-source-observation.yaml) — reserves the bitemporal observation boundary owned and served by qmf-data.
- [CT-11 — evidence persistence](contracts/ct-11-evidence-persistence.yaml) — reserves governed evidence persistence and retrieval.
- [CT-12 — dataset split](contracts/ct-12-dataset-split.yaml) — reserves dataset release, split, and sealed-holdout evidence.
- [CT-13 — journal](contracts/ct-13-journal.yaml) — reserves journal evidence without adopting mutation or storage semantics.
- [CT-14 — backup and restore](contracts/ct-14-backup-restore.yaml) — reserves provider-neutral transfer and restore evidence without completion or validation rules.
- [CT-15 — external source adapter](contracts/ct-15-external-source-adapter.yaml) — defines the active request/response boundary owned by qmf-data ingest.
- [CT-16 — indicator](contracts/ct-16-indicator.yaml) — defines the package-neutral two-mode indicator protocol and series vocabulary.
- [CT-17 — causal structure](contracts/ct-17-causal-structure.yaml) — defines the causal structure lifecycle and evidence boundary.
- [CT-18 — venue capabilities](contracts/ct-18-venue-capabilities.yaml) — defines the static capability declaration versus the per-account venue-observation profile and the capability field roster (DEC-0138).
- [CT-19 — venue command](contracts/ct-19-venue-command.yaml) — defines the four-kind command vocabulary, command identity, and the injective client-id mapping (DEC-0137).
- [CT-20 — venue event](contracts/ct-20-venue-event.yaml) — defines venue observations, the journal-event mapping and cardinality law, and reconciliation evidence (DEC-0137).
- [CT-21 — venue secret/session](contracts/ct-21-venue-secret-session.yaml) — defines the secret-reference lifecycle and session ownership shaped by AD-26 (DEC-0136).
- [CT-22 — Book/BMS charter](contracts/ct-22-book-charter.yaml) — reserves an unwired Book and BMS placeholder.
- [CT-23 — risk evaluation](contracts/ct-23-risk-evaluation.yaml) — reserves an unwired risk/refusal shape with no assigned caller.
- [CT-24 — Book mode](contracts/ct-24-book-mode.yaml) — preserves study-recap evidence only pending operator confirmation and GAP-0041.
- [CT-25 — risk journal](contracts/ct-25-risk-journal.yaml) — reserves an unwired risk-evidence placeholder not consumed by qmf-data.
- [CT-26 — store-to-backup input](contracts/ct-26-store-backup-input.yaml) — reserves the internal handoff from the data store to the backup component.

## Architecture decisions

- [ADR-0001 — authority and document-first](decisions/ADR-0001-authority-and-document-first.md) — records source authority and the documentation-before-implementation gate.
- [ADR-0002 — toolbox and V1 roster](decisions/ADR-0002-toolbox-and-v1-roster.md) — records QMF as a toolbox and fixes the final component roster.
- [ADR-0003 — definitions-only core](decisions/ADR-0003-definitions-only-core.md) — records the narrow, asset-neutral qmf-core boundary.
- [ADR-0004 — registry identity and lineage](decisions/ADR-0004-registry-identity-lineage.md) — records type-specific identity, graph-shaped lineage, and human promotion.
- [ADR-0005 — governed data evidence](decisions/ADR-0005-governed-data-evidence.md) — records bitemporal evidence, holdout, acquisition, journal, and durability boundaries.
- [ADR-0006 — indicators and structure](decisions/ADR-0006-indicators-and-structure.md) — separates wrapped indicator arithmetic from QMX-owned causal structure.
- [ADR-0007 — venue-neutral integration](decisions/ADR-0007-venue-neutral-integration.md) — records cTrader-first intent while preserving venue-neutral reserved seams.
- [ADR-0008 — Book and risk boundary](decisions/ADR-0008-book-and-risk-boundary.md) — records the fenced Book/BMS risk boundary and unresolved conflicts.
- [ADR-0009 — Book-level paper mode](decisions/ADR-0009-book-level-paper-mode.md) — preserves the study-recap paper-mode evidence caveat and rejects parallel Bot twins.
- [ADR-0010 — risk vocabulary restart](decisions/ADR-0010-risk-vocabulary-clean-start.md) — records the clean restart for R, SQS, formulas, and legacy risk terms.
- [ADR-0011 — deferred consumer products](decisions/ADR-0011-deferred-consumer-products.md) — keeps backtesting, simulator, MIS, QML, and agentic runtimes outside QMF V1.
- [ADR-0012 — runtime, packaging, and quality gates](decisions/ADR-0012-runtime-packaging-quality.md) — records the AD-1..AD-6 runtime matrix, uv workspace, toolchain, three tiers, two ladders, and dependency tiers.
- [ADR-0013 — exact values and identity](decisions/ADR-0013-exact-values-and-identity.md) — records AD-7..AD-12: exact money, exact time and calendars, instrument/venue/account identity, the fp1 fingerprint, typed refusals, and the result label with worlds.
- [ADR-0014 — performance, observability, concurrency](decisions/ADR-0014-performance-observability-concurrency.md) — records AD-13..AD-15: measure-then-budget performance, loud/traceable failure, and application-owned concurrency.
- [ADR-0015 — registry records and promotion](decisions/ADR-0015-registry-records-and-promotion.md) — records AD-16..AD-18: per-kind records and lineage, multiplicity at every layer, and the promotion-record skeleton.
- [ADR-0016 — data rooms, splits, journal, and the first edge](decisions/ADR-0016-data-rooms-splits-journal.md) — records AD-19..AD-21 plus the default-deny dependency direction and the ratified qmf-registry→qmf-data edge.

## Golden scenarios

- [SCN-0001 — core freeze gate](scenarios/SCN-0001-core-freeze-gate.md) — demonstrates that unresolved core choices block implementation.
- [SCN-0002 — source correction](scenarios/SCN-0002-source-correction.md) — demonstrates preservation of event time, knowledge time, source, and revision evidence.
- [SCN-0003 — sealed holdout](scenarios/SCN-0003-sealed-holdout.md) — demonstrates a sealed-test boundary whose reopening and one-look authority remain unresolved.
- [SCN-0004 — off-machine backup](scenarios/SCN-0004-off-machine-backup.md) — demonstrates the unresolved backup/restore evidence boundary without destructive authority.
- [SCN-0005 — uncertain venue submission](scenarios/SCN-0005-uncertain-venue-submission.md) — demonstrates the four-outcome law: a timeout mints an explicit `UNKNOWN` observation, the adapter blocks new commands on that stream and never self-clears, and resolution is an explicit application call (DEC-0137).
- [SCN-0006 — Book paper transition](scenarios/SCN-0006-book-paper-transition.md) — preserves the study evidence while blocking an unratified mode transition.
- [SCN-0007 — human promotion](scenarios/SCN-0007-human-promotion.md) — demonstrates that only a human may promote an artifact.
- [SCN-0008 — pair-scoped news](scenarios/SCN-0008-pair-scoped-news.md) — demonstrates the separation of pair-scoped news control from SQS.
- [SCN-0009 — synthetic stress](scenarios/SCN-0009-synthetic-stress.md) — demonstrates synthetic data as testing evidence rather than market truth.
- [SCN-0010 — risk conflicts](scenarios/SCN-0010-risk-boundary-conflicts.md) — demonstrates that Book/BMS and exit conflicts block risk implementation.

## Active lenses

- [Bug triage](lenses/bugs/triage.md) — defines evidence-preserving bug classification without inventing tools, owners, or remediation authority.
- [Data layer](lenses/data/data-layer.md) — maps data ownership, persistence, backup, acquisition, and unresolved schemas across components.
- [Logging and journal](lenses/observability/logging-spec.md) — defines evidence classes and logging ownership while keeping schemas and handoffs unresolved.
- [Metrics and alerts](lenses/observability/metrics-and-alerts.md) — identifies measurable subjects without inventing thresholds, SLOs, or automatic action.
- [Incident playbook](lenses/ops/incident-playbook.md) — defines evidence-preserving first responses without live or destructive authority.
- [Operations runbook](lenses/ops/runbook.md) — records operational no-op gates because no runtime or command suite is ratified.
- [Performance budgets](lenses/performance/budgets.md) — preserves the design workload case without turning it into an SLO.
- [Security model](lenses/security/security-model.md) — defines trust and human-authority boundaries while credential handling remains unresolved.
- [Fixture and scenario design](lenses/testing/fixtures-and-scenarios.md) — specifies how future fixtures and golden scenarios remain contract- and registry-bound.
- [Test strategy](lenses/testing/test-strategy.md) — defines future test layers and gates without inventing a toolchain or coverage threshold.
