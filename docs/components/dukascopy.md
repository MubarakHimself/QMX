---
id: COMP-DUKASCOPY
title: Dukascopy Historical Data Source
type: component-spec
status: provisional
component: COMP-DUKASCOPY
depends_on: []
decisions: [DEC-0009, DEC-0038, DEC-0051, DEC-0053, DEC-0107, DEC-0109, DEC-0117, DEC-0118, DEC-0119]
sources: [DEC-0009, DEC-0038, DEC-0051, DEC-0053, DEC-0107, DEC-0109, DEC-0117, DEC-0118, DEC-0119, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, docs/architecture/dependencies.yaml, docs/contracts/ct-15-external-source-adapter.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# Dukascopy Historical Data Source

`COMP-DUKASCOPY` is the external historical tick-source boundary selected directionally for the first backfill path. QMF owns the adapter and resulting evidence contracts; QMF does not own Dukascopy availability, source schema, licence, corrections, or historical coverage. [DEC-0051] [DEC-0053]

## Authority boundary

May, from QMF's perspective: supply a bounded historical source record to `COMP-QMF-DATA-INGEST` through CT-15 after source identity, fields, legal posture, and mapping rules are ratified. [DEC-0051] [DEC-0053]

May never, from QMF's perspective: be treated as QMF-owned; be assumed complete or legally retainable; replace later broker-source identity; silently merge disagreements with live observations; schedule or supervise QMF ingestion; or trigger a bulk corpus download during documentation or a factory feature pass. [DEC-0009] [DEC-0051] [DEC-0053]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Historical-source request / response | request in, response out | [CT-15](../contracts/ct-15-external-source-adapter.yaml) | COMP-QMF-DATA-INGEST |

## Behavior

Dukascopy is an active external CT-15 provider. `COMP-QMF-DATA-INGEST` is the QMF owner and caller: it sends a bounded request to Dukascopy and receives the provider response. `COMP-QMF-DATA` does not call or consume CT-15. Dukascopy-class history precedes forward broker capture in the acquisition sequence. QMF V1 supplies acquisition plumbing; the bulk history load remains a first-install or operator-run action outside the library lifecycle. [DEC-0051] [DEC-0053]

Every accepted observation retains its external source identity and is converted into CT-10 by the ingest seam. A later broker feed remains a separate source. Tick sources are separately identified (Dukascopy history versus the broker feed); bid and ask are preserved with their source timestamps, and disagreements between sources stay visible through `corroborates` and `disagrees-with` edges, never merged away. Every external fact carries event-time, known-at, source, and revision, and corrections are appended, never overwriting. [DEC-0038] [DEC-0053] [DEC-0119] [DEC-0117]

The adapter-versus-application boundary is ratified: qmf-data defines the source contract, normalization, validation, and idempotent intake keyed on `(source, source-native id, revision)` — a provider revision is a new artifact, never a fingerprint collision — while the standalone application owns scheduling, retries, supervision, and operator UI. [DEC-0119]

Raw originals and lineage are kept forever, and time-series is partitioned by source, instrument, and time window. [DEC-0118]

The source-identity, bid/ask-preservation, and disagreement-edge discipline is ratified (DEC-0119); the concrete Dukascopy provider schema — symbol list, depth, and per-symbol bid/ask specifics — is documentation-time detail for the ingest mapping, and the legal retention/licence posture remains an open operator item recorded, not resolved here.

<!-- no-diagram: the external source exposes one CT-15 seam and has no QMF-owned internal structure -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Instrument identity shape | `registry:instrument_identity_shape` | Identity is (venue, venue's own symbol), the symbol opaque and never parsed; the historical source is a `source`, distinct from any tradable `VenueId`. [DEC-0107] |
| Raw-history retention | `registry:raw_history_retention_policy` | Raw originals and lineage are kept forever, partitioned by source, instrument, and time window; the policy governs accepted QMF evidence and grants no source licence rights. [DEC-0118] |
| External source identity and legal settings | — | Source-identity, bid/ask-preservation, and disagreement-edge discipline ratified (DEC-0119); the concrete provider schema is documentation-time detail for the ingest mapping, and the legal-retention posture is an open operator item. |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | The source is unavailable or a bounded transfer stops. | QMF cannot require external recovery; checkpoint, retry, and operator-visible refusal live in the standalone application that owns scheduling and supervision. | DEC-0051, DEC-0119 |
| FM-2 | A record is malformed, missing required timestamps, or cannot map to a source-qualified instrument. | The ingest seam must not admit it as valid evidence; it returns an `invalid input` refusal from the ratified seven-category taxonomy. The concrete quarantine schema is documentation-time detail. | DEC-0038, DEC-0053, DEC-0109 |
| FM-3 | Duplicate, overlapping, or conflicting records are observed. | QMF must not overwrite or silently merge earlier evidence; the idempotent `(source, source-native id, revision)` intake keys each as an artifact, and disagreements stay visible through `corroborates` / `disagrees-with` edges. | DEC-0038, DEC-0053, DEC-0119 |
| FM-4 | Source licence or long-term retention rights are unconfirmed. | Acquisition must not be operationalized on an invented legal assumption; the legal-retention posture is an open operator item recorded, not resolved here. | DEC-0051, DEC-0119 |
| FM-5 | A request attempts to download the complete corpus during documentation or the factory pass. | The request is outside this component pass; only bounded adapter evidence is permitted until installation/runbook execution. | DEC-0051 |

## Related

Decisions: DEC-0009, DEC-0038, DEC-0051, DEC-0053, DEC-0107, DEC-0117, DEC-0118, DEC-0119. Scenarios: [SCN-0002 source correction](../scenarios/SCN-0002-source-correction.md). Knowledge: none drafted.
