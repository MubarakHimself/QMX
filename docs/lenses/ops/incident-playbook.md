---
id: OPS-INCIDENT-QMF-V1
title: QMF V1 Incident Playbook
type: runbook
status: provisional
depends_on: [COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0001, DEC-0003, DEC-0009, DEC-0029, DEC-0033, DEC-0035, DEC-0038, DEC-0041, DEC-0042, DEC-0045, DEC-0048, DEC-0059, DEC-0065, DEC-0096]
sources: [DEC-0001, DEC-0003, DEC-0009, DEC-0029, DEC-0033, DEC-0035, DEC-0038, DEC-0041, DEC-0042, DEC-0045, DEC-0048, DEC-0059, DEC-0065, DEC-0096, _docwork/gaps.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-09-registry-persistence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-11-evidence-persistence.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-25-risk-journal.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF V1 Incident Playbook

QMF V1 has no deployed runtime or ratified alerting system, so this playbook defines evidence-preserving first responses without inventing commands or operational authority. The operator's direct ruling controls any intervention that the ledger does not authorize. [DEC-0001] [DEC-0009]

## Incident authority

Only a human may promote an artifact into live money. No agent, detector, alert, adapter, external acknowledgement, or incident condition grants permission to trade, flatten, change Book mode, rotate secrets, restore over data, or bypass a contract. [DEC-0041] [DEC-0049]

`GAP(GAP-0036): Define venue-outage response, retries, reconciliation, VPS-failure behavior, and flattening authority before any live incident procedure exists.`

`GAP(GAP-0040): Resolve exit ownership before an incident procedure can invoke an exit.`

`GAP(GAP-0041): Define live/paper transitions, rollback, duplicate prevention, and account authority before an incident procedure can change Book mode.`

`GAP(GAP-0046): Define same-tick priority before an incident procedure can order protective, force-flat, kill-switch, invalidation, or discretionary actions.`

## Universal first response

1. Do not invent a recovery command or retry policy.
2. Preserve already-existing source and CT-13 evidence without assuming the reserved, unwired CT-25 seam has produced anything. [DEC-0038] [DEC-0048]
3. Do not overwrite raw evidence, lineage, or registry history. [DEC-0035] [DEC-0045]
4. Do not initiate or retry a credential-bearing operation while secret storage, injection, redaction, and lifecycle rules remain unresolved under GAP-0035.
5. Stop at the human authority boundary when a response can affect live money, account mode, data restoration, credentials, or external state. [DEC-0001] [DEC-0041]

## Failure classes and first responses

| Failure class | Evidence to preserve | Safe first response | Unresolved authority or behavior |
|---|---|---|---|
| Contract or invariant refusal | CT-04 refusal, contract version, input fingerprint, and available caller evidence. | Keep the refusal intact; do not coerce the input or invent retryability. | `GAP(GAP-0011): Define refusal fields, retryability, redaction, and exception mapping.` |
| Causality or registration failure | CT-08 gate evidence, CT-06 request identity, CT-07 lineage, and source knowledge time. | Keep the artifact unregistered and unpromoted. | `GAP(GAP-0016)` `GAP(GAP-0017)` `GAP(GAP-0019)` |
| External data-source outage or malformed feed | CT-15 source identity, last valid CT-10 observation, provider response, and gap/duplicate evidence. | Do not manufacture observations or merge another source silently. | `GAP(GAP-0028)` through `GAP(GAP-0030)` |
| Persistence or journal failure | Failed CT-09, CT-11, or CT-13 operation and the identity of evidence not confirmed durable. | Do not write a private fallback store or report durability without verification. | `GAP(GAP-0021)` `GAP(GAP-0022)` `GAP(GAP-0025)` `GAP(GAP-0026)` |
| Backup or restore failure | Any provider acknowledgement or object evidence that already exists; CT-14 completion and validation fields are unresolved. | Perform no destructive restore and make no recoverability claim. | `GAP(GAP-0027): Define provider response, RPO, RTO, retention, validation, restore authority, and escalation.` |
| Secret/session failure | The affected external boundary; CT-21 has no operational schema. | Stop at the no-operation gate; do not initiate, retry, or recover a credential-bearing operation. | `GAP(GAP-0035): Define storage, injection, redaction, expiry, rotation, revocation, compromise, and response authority.` |
| Venue command or state uncertainty | No active CT-19 command/CT-20 event handoff exists; preserve any external observation independently available. | Implementation is blocked. Do not manufacture success, retry, infer permission, or flatten. | `GAP(GAP-0036): Define the complete command state and transition table, identities, read-back/cursors, retry/duplicate rules, terminal and uncertain states, new-command gate, journal evidence, and human flattening authority.` `GAP(GAP-0038)` `GAP(GAP-0039)` |
| Risk, exit, SQS, news, stop-out, or Book-mode ambiguity | CT-22 through CT-25 are reserved placeholders, not active evidence handoffs. | Produce no risk authorization or transition. CT-24 remains evidence-only until operator confirmation and GAP-0041; CT-25 is not wired to Data. | `GAP(GAP-0039)` through `GAP(GAP-0046)` |

## What “down” means

| Subject | “Down” or unavailable means | Evidence boundary |
|---|---|---|
| QMF library | Its documented contract or conformance tests cannot be satisfied; no runtime-health meaning is implied. | Component test/reference evidence required by DEC-0096. |
| Registry | Registration, lineage, gate evidence, or persistence cannot be confirmed through CT-06 through CT-09. | No artifact is treated as registered or promoted. [DEC-0033] [DEC-0041] |
| Data | Source observations, evidence persistence, dataset access, or journal contracts cannot be confirmed; CT-14 is separately owned by COMP-QMF-DATA-BACKUP. | No private store or invented observation substitutes for CT-10 through CT-13, and no CT-14 completion or restore behavior is inferred. [DEC-0042] [DEC-0048] |
| Venue | Runtime health is undefined because CT-18 through CT-21 are reserved and unwired. | CT-19 has no assigned caller or authorization evidence; CT-20 has no active consumer. External cTrader remains authoritative only for observations it actually reports. [DEC-0059] |
| Risk | Runtime health is undefined because CT-22 through CT-25 are reserved and unwired. | CT-23 has no caller, CT-24 is evidence-only pending confirmation, and CT-25 is not wired to Data; no authorization, exit, or transition is inferred. [DEC-0065] |
| External provider | The QMF boundary cannot obtain a verified response from COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, or COMP-OBJECT-STORAGE. | QMF cannot command the provider to recover or claim provider-internal state. |

## Evidence and escalation

CT-13 is the journal boundary; CT-25 is only a reserved, unwired risk-evidence placeholder. Event kinds, correlation fields, cadence, retention, redaction, ordering, consumers, and query guarantees remain `GAP(GAP-0025)` and `GAP(GAP-0026)`; an agent must not invent them. [DEC-0048]

No severity tiers, paging targets, notification channels, incident commander, responder role, or automatic action is ratified. Any live-money or destructive response stops at the operator. Venue flattening remains GAP-0036; exits remain GAP-0040; paper-mode changes remain GAP-0041; action priority remains GAP-0046. [DEC-0001]

## Recovery completion

An incident is not resolved merely because a process responds. Library conformance evidence is required where defined, but venue reconciliation, risk-journal handoff, backup completion, restore validation, closure, and sign-off rules remain unresolved; CT-20, CT-25, and CT-14 cannot be treated as completed operational evidence paths. [DEC-0045] [DEC-0096]
