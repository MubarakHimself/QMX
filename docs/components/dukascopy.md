---
id: COMP-DUKASCOPY
title: Dukascopy Historical Data Source
type: component-spec
status: provisional
component: COMP-DUKASCOPY
depends_on: []
decisions: [DEC-0009, DEC-0038, DEC-0051, DEC-0053]
sources: [DEC-0009, DEC-0038, DEC-0051, DEC-0053, docs/architecture/dependencies.yaml, docs/contracts/ct-15-external-source-adapter.yaml]
generated: 2026-08-18
verified: 2026-08-18
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

Every accepted observation retains its external source identity and is converted into CT-10 by the ingest seam. A later broker feed remains a separate source. [DEC-0038] [DEC-0053]

`GAP(GAP-0028): Ratify the adapter-versus-application boundary for invocation, retries, checkpoints, and lifecycle.`

`GAP(GAP-0030): Verify source fields, symbols, depth, bid/ask representation, timestamps, checksums, duplicates, gaps, legal retention, and reconciliation before adapter implementation.`

<!-- no-diagram: the external source exposes one CT-15 seam and has no QMF-owned internal structure -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Instrument identity shape | `registry:instrument_identity_shape` | Null until GAP-0009 defines QMF identity mapping. |
| Raw-history retention | `registry:raw_history_retention_policy` | Governs accepted QMF evidence; it does not grant source licence rights. |
| External source identity and legal settings | — | `GAP(GAP-0030): No provider schema or legal-retention configuration is ratified.` |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | The source is unavailable or a bounded transfer stops. | QMF cannot require external recovery. `GAP(GAP-0028): Define checkpoint, retry, and operator-visible refusal behavior.` | DEC-0051 |
| FM-2 | A record is malformed, missing required timestamps, or cannot map to a source-qualified instrument. | The ingest seam must not admit it as valid evidence. `GAP(GAP-0030): Define the CT-15 refusal and quarantine evidence.` | DEC-0038, DEC-0053 |
| FM-3 | Duplicate, overlapping, or conflicting records are observed. | QMF must not overwrite or silently merge earlier evidence. `GAP(GAP-0030): Define duplicate and reconciliation rules.` | DEC-0038, DEC-0053 |
| FM-4 | Source licence or long-term retention rights are unconfirmed. | Acquisition must not be operationalized on an invented legal assumption. `GAP(GAP-0030): Record the approved posture.` | DEC-0051 |
| FM-5 | A request attempts to download the complete corpus during documentation or the factory pass. | The request is outside this component pass; only bounded adapter evidence is permitted until installation/runbook execution. | DEC-0051 |

## Related

Decisions: DEC-0009, DEC-0038, DEC-0051, DEC-0053. Scenarios: [SCN-0002 source correction](../scenarios/SCN-0002-source-correction.md). Knowledge: none drafted.
