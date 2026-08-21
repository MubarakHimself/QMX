---
id: OPS-INCIDENT-QMF-V1
title: QMF V1 Incident Playbook
type: runbook
status: ratified
depends_on: [COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0001, DEC-0003, DEC-0009, DEC-0029, DEC-0033, DEC-0035, DEC-0038, DEC-0041, DEC-0042, DEC-0045, DEC-0048, DEC-0059, DEC-0065, DEC-0096, DEC-0106, DEC-0109, DEC-0112, DEC-0114, DEC-0116, DEC-0117, DEC-0118, DEC-0119, DEC-0121, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0142, DEC-0143, DEC-0147, DEC-0149, DEC-0150, DEC-0151, DEC-0152, DEC-0153, DEC-0155, DEC-0157, DEC-0158]
sources: [DEC-0001, DEC-0003, DEC-0009, DEC-0029, DEC-0033, DEC-0035, DEC-0038, DEC-0041, DEC-0042, DEC-0045, DEC-0048, DEC-0059, DEC-0065, DEC-0096, DEC-0106, DEC-0109, DEC-0112, DEC-0119, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/time-audit-devops.md, _docwork/gaps.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-09-registry-persistence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-11-evidence-persistence.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-25-risk-journal.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF V1 Incident Playbook

QMF V1 has no deployed runtime or ratified alerting system, so this playbook defines evidence-preserving first responses without inventing commands or operational authority. The operator's direct ruling controls any intervention that the ledger does not authorize. [DEC-0001] [DEC-0009]

## Incident authority

Only a human may promote an artifact into live money. No agent, detector, alert, adapter, external acknowledgement, or incident condition grants permission to trade, flatten, change Book mode, rotate secrets, restore over data, or bypass a contract. [DEC-0041] [DEC-0049]

The venue command law is ratified (DEC-0137): venue outage is fail-closed — on disconnect in-flight commands become `UNKNOWN`, command retry is prohibited (retryability rides typed refusals), reconciliation is an on-demand read-back gating the command pipe only, and session recovery never resubmits a command. Flatten is mechanical `close_position`/`close_all` the adapter never initiates; flatten authority is assigned — the operator always, Book policy through pre-declared triggers, the protection authority per the node's severity policy, nobody else (DEC-0150) — while the trigger→level→effect matrix and reconciliation-verdict consequences stay node/risk sitting territory, tracked in `tracker/trading-node-notes.md` (DEC-0142).

## Ratified control-action semantics

Two different things, named apart, never merged (DEC-0150): the **kill switch** is the global black-swan authority — it stops all *new* trading everywhere, live and paper alike, escalates automatically, and **de-escalates only by a human**; its effect may additionally be `drain` or `close_all`, which effect a severity carries being the node's severity policy to choose. The **kill line** is a per-Book capital floor — breaching it automatically flattens that binding's scope and stands the Book down, so a 3am breach never waits for the operator.

The **exit-preservation invariant** is spine-level law: no control action, of any authority, at any scope, may block a risk-reducing act — `cancel_order`, `close_position`, `close_all`, a risk-non-increasing `amend_protection`, a protection action, or the recording of evidence. The blocking half of any control is always **entries only** (DEC-0150). During an incident this means a control never traps a position behind itself.

`resume` is **operator-only**: escalation automates, de-escalation does not (DEC-0150).

**Standing intent, not a queue** (DEC-0150): a protection action is journaled **before** dispatch, so the intent exists even if nothing reaches the venue, and "is this account under a standing flatten intent" is a restart-proof read-time fold. On reconnect the node re-evaluates every standing intent against reconciled state and, if still unsatisfied, issues a **new command with a new identity** — **re-deciding is not retrying**. The intent never time-expires. `flatten` satisfies only on a `reconciled` verdict showing the scope flat; a command outcome never satisfies an intent, and `drift`, `unknown`, and `out-of-lookback` verdicts alarm and **hold the intent open without dispatching** (DEC-0150, DEC-0158). An undeliverable protection act alarms loudly carrying the manual fallback, and the intent stays open.

A protection act refused by an `UNKNOWN` block **never evaporates** — it stands as a standing intent and is re-decided when the block clears (DEC-0158).

Which effect fires at which severity is node authority: QMF carries the contract, the scopes, the refusals, and the evidence, never the trigger→level→effect matrix (DEC-0150), which stays in `tracker/trading-node-notes.md` (DEC-0142).

## Universal first response

1. Do not invent a recovery command or retry policy.
2. Preserve the typed refusal intact: every public operation succeeds or **returns** a typed refusal carrying category, machine-readable context, and retryability; refusals and errors always carry context and are never swallowed (DEC-0109, DEC-0112).
3. Preserve already-existing source and CT-13 journal-stream evidence without assuming the reserved, unwired CT-25 seam has produced anything. [DEC-0038] [DEC-0048] [DEC-0119]
4. Do not overwrite raw evidence, lineage, or registry history. [DEC-0035] [DEC-0045]
5. Never surface a secret value: QMF handles opaque secret references, and only the connection manager holds values in memory; refusal context, logs, health reports, and metrics carry the reference id only (DEC-0136). On a credential compromise, follow the compromise-recovery drill below rather than improvising.
6. Do not retry a venue command or clear an `UNKNOWN`: command retry is prohibited and only an explicit application `resolve_unknown` call unblocks a stream — the adapter never self-clears (DEC-0137).
7. Stop at the human authority boundary when a response can affect live money, account mode, data restoration, credentials, or external state. [DEC-0001] [DEC-0041]

## Failure classes and first responses

| Failure class | Evidence to preserve | Safe first response | Unresolved authority or behavior |
|---|---|---|---|
| Contract or invariant refusal | The returned CT-04 typed refusal (category, machine-readable context, retryability), contract format version, input fingerprint, and available caller evidence. | Keep the refusal intact; do not coerce the input or invent retryability. The refusal is returned, never raised across a package boundary (DEC-0109, DEC-0112). | Refusal categories are ratified (seven categories, DEC-0109); no gap remains at the taxonomy level. |
| Clock or time-sync failure | The drift measurement or unsynchronized state, the affected suspect window, and the data-gap record. | Node/ops obligation: exceeding a drift band is a typed refusal plus a journal record plus a node state change; an unsynchronized/stepped/paused window is an explicit data-gap and no-trade window. Do not trade before sync is confirmed, and do not stamp events from a foreign clock (DEC-0106, DEC-0112). | Node/ops sitting owns the numeric drift bands, chrony provisioning, and slew-only-while-live enforcement (companion `time-audit-devops.md`). |
| Causality or registration failure | CT-08 event-time/known-at ingredients, CT-06 request identity, CT-07 lineage, and source knowledge time. | Keep the artifact unregistered and unpromoted; the bitemporal ingredients and the promotion-record skeleton are ratified (DEC-0114, DEC-0116) while the look-ahead gate is deferred. | `GAP(GAP-0016)` `GAP(GAP-0017)` deferred to the backtesting sitting (DEC-0121); the promotion evidence checklist accretes from later sittings. |
| External data-source outage or malformed feed | CT-15 source identity, last valid CT-10 observation, provider response, and gap/duplicate evidence. | Do not manufacture observations or merge another source silently; source disagreements stay visible via `corroborates`/`disagrees-with` edges, never merged (DEC-0119). | Adapter boundary and idempotent intake are ratified (DEC-0119); the provider legal archiving posture remains an open operator item, the cTrader trendbar price basis is measured per broker at first connection under the verify-or-refuse suite (DEC-0135), and scheduling/retries are application-owned. |
| Persistence or journal failure | Failed CT-09, CT-11, or CT-13 operation and the identity of evidence not confirmed durable; a per-(writer, boot-epoch) journal sequence gap signals loss. | Do not write a private fallback store or report durability without verification. A store-library exception is translated to a `storage failure` typed refusal at the qmf-data boundary, never propagated (DEC-0109). | Store stack, migration process, journal streams, and retention are ratified (DEC-0117, DEC-0118, DEC-0119); numeric retention windows are set after measured volume. |
| Backup or restore failure | Any provider acknowledgement or object evidence that already exists; the CT-14 backup design is nightly, encrypted, versioned, off-machine. | Perform no destructive restore and make no recoverability claim; restore and cutover execution are application/ops-owned. | Backup design ratified (DEC-0118); numeric RPO/RTO, retention, encryption key custody, and restore authority are named at the node/ops sitting. |
| Secret/session failure | The affected credential's opaque reference id (never the value); the CT-21 session and rotation state; any alarm from a failed store after rotation. | Run the compromise-recovery drill below; never surface a secret value. A failed store after rotation is an alarm **and** a command-pipe block (`unavailable dependency`, after-condition = successful store or operator re-provision) with the **sensing pipe unaffected** (DEC-0136). One live refresher per credential — a workstation tool never refreshes a credential a VPS session owns. | Store mechanics and key custody land at the node/ops sitting; credential entry/management UI is platform territory (DEC-0136). |
| Venue command or state uncertainty | The explicit `UNKNOWN` observation (trigger `timeout` \| `transport-error` \| `disconnect`, the monotonic elapsed measurement, the wall receive instant, the submission deadline in force), the command `fp1`, and every verbatim venue event recorded before interpretation. | The adapter refuses new commands on that `(VenueId, account)` stream while an `UNKNOWN` is outstanding (`transient venue failure`); do not retry, manufacture success, infer permission, or flatten. Unblock **only** via an explicit application `resolve_unknown(command identity, resolution ∈ observed-accepted \| observed-absent \| operator-attested)` call after a reconciliation read-back — the adapter never self-clears (DEC-0137). Sensing stays live throughout. | When reconciliation runs and what a verdict (`reconciled` \| `drift` \| `unknown` \| `out-of-lookback`) triggers stay node/risk sitting territory (DEC-0142); the command caller is the account-facing risk layer, ratified as **defined-unwired** surface (DEC-0143), and flatten authority is assigned (DEC-0150). |
| Risk, exit, SQS, news, bench, or Book-mode ambiguity | CT-22 through CT-25 and CT-27 through CT-32 are ratified surface, **defined-unwired** — no active evidence handoff yet. | Produce no risk authorization or transition from these docs; the contracts are ratified but no code exists and implementation arrives only through the factory pipeline. CT-24 is evidence-only; CT-25 stays unwired to Data. | Exits (DEC-0147), paper mode (DEC-0149), control actions (DEC-0150), priority (DEC-0151), windows (DEC-0152), SQS (DEC-0153), and bench (DEC-0155) are ratified; wiring is node/risk territory (DEC-0142). |

## Ratified venue incident procedures

Two venue procedures are ratified as documented, tested contract-level shapes. They define QMF-owned behavior only; when a step runs in production, its scheduling, verdict consequences, and flatten authority are node/risk sitting territory, tracked in `tracker/trading-node-notes.md` (DEC-0142). These procedures are ratified design; implementation authorization arrives only through the factory pipeline.

### Credential compromise-recovery drill (DEC-0136)

The compromise drill ships as tested behavior; expiry and refusal paths are tested, and testing uses demo credentials only — factory sandboxes never hold live secrets. No step surfaces a secret value; only the reference id appears in logs and refusals.

1. **Venue-side invalidation.** cTID re-authorization invalidates **all** outstanding refresh tokens (the never-expiring refresh token is the crown-jewel secret, DEC-0135); cTID re-authorization is the invalidation anchor.
2. **Application-credential reset.** Reset the cTrader application credentials.
3. **Store replacement.** Replace the credential in the deployment environment's protected store (atomic replace through the connection manager's `SecretStore` port).
4. **Session restart.** Restart the venue session under the replaced credential.

Where a venue already invalidated the old refresh material during rotation, the session is marked degraded and this drill triggers automatically (DEC-0136).

### `UNKNOWN`-resolution procedure (DEC-0137)

An `UNKNOWN` is a state, never an error; a transport error, timeout, or disconnect yields it. No QMF component retries, assumes an outcome, flattens, or invents a terminal state on `UNKNOWN`.

1. **Preserve the record.** Recording precedes interpretation: the `UNKNOWN` was minted as an explicit observation (trigger, monotonic elapsed measurement, wall receive instant, submission deadline) and journaled before any state evaluation; keep it intact.
2. **Honor the block.** While the `UNKNOWN` is outstanding, the adapter refuses new commands on that `(VenueId, account)` stream (`transient venue failure`); `suspend-new` takes local effect instantly; **sensing stays live**.
3. **Read back.** Produce an on-demand reconciliation read-back of venue orders, fills, positions, and balance over a stated lookback (equity derived where the venue has no native field); reconciliation gates the command pipe only.
4. **Resolve explicitly.** The application issues `resolve_unknown(command identity, resolution ∈ observed-accepted | observed-absent | operator-attested)` — the adapter never self-clears; the block is per command and clears on resolution, never on a reconciliation verdict.
5. **Cancel-versus-fill rule.** A cancel resolved by read-back is `accepted-by-venue` only if the read-back also shows no fill for that order at or after the cancel's submit stamp; otherwise it resolves `rejected-by-venue (superseded-by-fill)`.

When reconciliation runs and what a verdict (`reconciled` \| `drift` \| `unknown`) triggers are node/BMS authority (DEC-0142).

## What “down” means

| Subject | “Down” or unavailable means | Evidence boundary |
|---|---|---|
| QMF library | Its documented contract or conformance tests cannot be satisfied; no runtime-health meaning is implied. | Component test/reference evidence required by DEC-0096. |
| Registry | Registration, lineage, gate evidence, or persistence cannot be confirmed through CT-06 through CT-09. | No artifact is treated as registered or promoted. [DEC-0033] [DEC-0041] |
| Data | Source observations, evidence persistence, dataset access, or journal contracts cannot be confirmed; CT-14 is separately owned by COMP-QMF-DATA-BACKUP. | No private store or invented observation substitutes for CT-10 through CT-13, and no CT-14 completion or restore behavior is inferred. [DEC-0042] [DEC-0048] |
| Venue | The connection manager cannot maintain a session (heartbeat, token refresh, reconnect fail) or an `UNKNOWN` is outstanding and blocking a `(VenueId, account)` command stream; the command pipe may be blocked while sensing stays live (DEC-0137). | Venue events are recorded verbatim before interpretation; the caller stays unassigned in QMF and external cTrader is authoritative only for observations it actually reports. [DEC-0059] |
| Risk | Runtime health is undefined because the risk contracts are ratified but **defined-unwired** (no code; composition-root mediated). | CT-23 has no live caller, CT-24 is evidence-only, and CT-25 is not wired to Data; no authorization, exit, or transition is inferred from these docs (DEC-0143, DEC-0145). [DEC-0065] |
| External provider | The QMF boundary cannot obtain a verified response from COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, or COMP-OBJECT-STORAGE. | QMF cannot command the provider to recover or claim provider-internal state. |

## Evidence and escalation

CT-13 is the ratified journal boundary — N append streams, one per producing component under its `WriterId`, recording seven event types (decision, order, fill, risk transition, promotion, data quality, control action), with `correlation_id` a linking annotation excluded from `fp1` identity (DEC-0119). CT-25 is only a reserved, unwired risk-evidence placeholder. Numeric retention windows, redaction rules, and query guarantees are set after measured volume and are per-contract detail; an agent must not invent them. [DEC-0048] [DEC-0119]

No severity tiers, paging targets, notification channels, incident commander, responder role, or automatic action is ratified. Any live-money or destructive response stops at the operator. Flatten is mechanical `close_position`/`close_all` the adapter never initiates; flatten authority is assigned — the operator always (inalienable), Book policy through pre-declared triggers, the protection authority per the node's severity policy, nobody else (DEC-0150) — while the trigger→level→effect matrix stays node/risk sitting territory (DEC-0142). Exit ownership (DEC-0147), paper-mode changes (DEC-0149), and same-tick action priority (DEC-0151) are ratified as **defined-unwired** contract surface; their wiring is node/risk territory. [DEC-0001]

## Recovery completion

An incident is not resolved merely because a process responds. Library conformance evidence is required where defined. The venue reconciliation shape and verdict vocabulary (`reconciled` \| `drift` \| `unknown`) are ratified (DEC-0137), and on outage recovery, recovered fills commit through evidence before a session reports healthy — even a no-gap reconnect emits correlation evidence; but **when reconciliation runs and what a verdict triggers are node/BMS authority** (DEC-0142). The risk-journal handoff is ratified as read-time projections joined through the command record's content fingerprint but stays **defined-unwired** (DEC-0145); backup completion, restore validation, closure, and sign-off rules remain unresolved; CT-25 and CT-14 cannot be treated as completed operational evidence paths. [DEC-0045] [DEC-0096]
