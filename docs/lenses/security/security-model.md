---
id: SECURITY-MODEL-QMF-V1
title: QMF V1 Security Model
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0001, DEC-0009, DEC-0029, DEC-0030, DEC-0035, DEC-0038, DEC-0041, DEC-0042, DEC-0045, DEC-0048, DEC-0059, DEC-0065]
sources: [DEC-0001, DEC-0009, DEC-0029, DEC-0030, DEC-0035, DEC-0038, DEC-0041, DEC-0042, DEC-0045, DEC-0048, DEC-0059, DEC-0065, _docwork/gaps.yaml, docs/architecture/dependencies.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-25-risk-journal.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF V1 Security Model

QMF V1 concentrates authority at explicit contract seams: humans control live promotion, backend risk semantics never originate in external adapters, middleware translates but does not decide, data stores hold evidence but no business rule, and external providers remain outside QMF control. [DEC-0009] [DEC-0041] [DEC-0059] [DEC-0065]

## Security status

This design has no ratified authentication fields, authorization tokens, secret locations, key stores, roles, deployment identities, alert thresholds, or live account. This document grants no live access, credential use, order submission, flattening, promotion, restore, or destructive mutation authority.

## Trust boundaries

| Boundary | Trusted claim | Untrusted or unresolved claim | Governing evidence |
|---|---|---|---|
| Human operator → registry/live zone | Only a human may promote an artifact into live money. | Identity, signature, role, and approval payload remain unresolved. | CT-06; `GAP(GAP-0019)` [DEC-0041] |
| Middleware → backend | COMP-QMF-DATA-INGEST may produce CT-10 into COMP-QMF-DATA; COMP-QMF-VENUE may also produce CT-10 into COMP-QMF-DATA. | Downstream components consume CT-10 from Data, never depend on Data-Ingest; CT-18 through CT-21 are reserved and unwired. Middleware may not create risk permission or provider facts. | CT-10, CT-15, CT-18 through CT-21 [DEC-0059] |
| Backend → data | Backend components may use ratified persistence seams; CT-25 is not yet wired to Data. | Data components may not own identity, promotion, risk, or other business rules; no CT-25 handoff is active. | [DEC-0035] [DEC-0042] [DEC-0048] |
| Backup process → object storage | CT-14 reserves a future transfer/restore evidence boundary. | Completion, validation, provider access, and destructive restore authority remain unresolved. | `GAP(GAP-0027)` [DEC-0045] |
| QMF → external providers | QMF may call only ratified adapters and record observed outcomes. | QMF cannot control provider availability, schema, legal posture, credential state, or execution result. | CT-14, CT-15, CT-18 through CT-21 |
| Out-of-scope QMX application → venue (reserved) | CT-19 reserves a transport shape; no QMF V1 caller, authorization producer, or authorization-evidence owner is assigned. | No Risk-to-Venue active wiring and no live command are buildable. | `GAP(GAP-0036)` `GAP(GAP-0038)` `GAP(GAP-0039)` [DEC-0059] [DEC-0065] |

## Authorization rules

| Interface | Authorized actor or producer | Prohibited action | Open definition |
|---|---|---|---|
| CT-06 registration/promotion | Registration is owned by COMP-QMF-REGISTRY; live promotion is human-only. [DEC-0041] | Automated promotion or treating a test result as approval. | `GAP(GAP-0019): Define reviewer identity, signature, evidence, and live-zone transition.` |
| CT-14 backup/restore | No operational actor is authorized by this provisional document. | Restoring over data, deleting evidence, or claiming completion/validation. | `GAP(GAP-0027)` |
| CT-15 source ingest | COMP-QMF-DATA-INGEST accepts only a ratified source mapping. | Treating provider identity, licence, or data as trusted by default. | `GAP(GAP-0029)` `GAP(GAP-0030)` |
| CT-19 venue command | Caller and authorization evidence are unassigned; the eventual caller is an out-of-scope QMX application. | Building a live command, permission, sizing, retry, recovery, or flattening path. | `GAP(GAP-0036)` `GAP(GAP-0038)` `GAP(GAP-0039)` |
| CT-21 secret/session | No actor: CT-21 is an interim no-operation gate. | Any credential-bearing integration while location, storage, injection, redaction, and lifecycle rules are unresolved. | `GAP(GAP-0035)` |
| CT-22 through CT-25 risk seams | No active caller or consumer; these are reserved placeholders. | Implementing or invoking unresolved Book/BMS, exit, paper-mode, formula, journal, or priority behavior. CT-24 is evidence-only pending operator confirmation; CT-25 is not wired to Data. | `GAP(GAP-0039)` through `GAP(GAP-0046)` |

## Secret inventory

No secret value or secret location is documented.

| Secret class | Intended consumer | Location | Rotation/revocation | Governing gap |
|---|---|---|---|---|
| cTrader application credentials | No active consumer | Location and storage unratified; no credential-bearing operation permitted. | Injection, redaction, expiry, refresh, rotation, revocation, and compromise response unratified. | GAP-0035 |
| cTrader access/refresh/session material | No active consumer | Location and storage unratified; no credential-bearing operation permitted. | Injection, redaction, expiry, refresh, rotation, revocation, and compromise response unratified. | GAP-0035 |
| Object-storage credentials and encryption material | No operational consumer authorized here | Location and storage unratified; no credential-bearing operation permitted. | Injection, redaction, rotation, revocation, and compromise response unratified. | GAP-0027 |
| Calendar-provider credentials, if required | Standalone recorder / COMP-CALENDAR-FEED boundary | Unratified. | Unratified with provider and legal posture. | GAP-0029 |
| Historical-source credentials, if required | COMP-QMF-DATA-INGEST / COMP-DUKASCOPY boundary | Unratified. | Unratified with source contract. | GAP-0030 |

## Threats and required controls

| Threat | Required security property | Current boundary |
|---|---|---|
| Secret disclosure in evidence | No credential-bearing integration proceeds while GAP-0035 is open. | Location, storage, injection, redaction, and lifecycle are unresolved; no recommendation is adopted as a settled control. |
| Unauthorized live promotion | Only a human may promote, and promotion evidence must be immutable. [DEC-0041] | Reviewer/signature fields remain GAP-0019. |
| Confused-deputy order submission | CT-19 is reserved and unwired; no caller or authorization evidence exists. [DEC-0059] [DEC-0065] | Authorization source, complete command state table, idempotency, refusal, and human flattening authority remain GAP-0036 through GAP-0039; no live command is buildable. |
| Replay or duplicate command | No duplicate behavior may be assumed. | Idempotency and reconciliation remain GAP-0036. |
| Look-ahead or stale evidence | Event time and knowledge time stay distinct and CT-08 checks causality. [DEC-0038] | Claim, cutoff, stale, and pass/refusal evidence remain GAP-0016 and GAP-0023. |
| Evidence tampering or overwrite | Versioned lineage must preserve earlier evidence, but CT-13/CT-25 journal mutation semantics are not inferred. Incompatible semantics mint new versions. [DEC-0030] [DEC-0035] [DEC-0045] | Schemas, transactions, journal semantics, migrations, compaction, retention, and validation remain GAP-0015 and GAP-0021 through GAP-0027. |
| External-source impersonation or schema drift | Every observation retains source identity and contract version; QMF never assumes provider semantics. | Provider identity, legal posture, fields, and correction behavior remain GAP-0029, GAP-0030, GAP-0037, and GAP-0038. |
| Automated incident action exceeds authority | No alert or detector grants promotion, flattening, exit, restore, or mode-transition permission. [DEC-0041] | Venue/risk incident authority remains GAP-0036 and GAP-0039 through GAP-0046. |

## Audit evidence

CT-13 is the journal boundary; CT-25 is only a reserved, unwired future risk-evidence placeholder. Event fields, identities, cadence, retention, redaction, ordering, consumers, and query guarantees remain `GAP(GAP-0025)` and `GAP(GAP-0026)`. No credential-bearing operation is permitted while GAP-0035 is open. [DEC-0048]
