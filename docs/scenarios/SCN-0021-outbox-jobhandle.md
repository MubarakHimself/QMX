---
id: SCN-0021
title: Durable outbox successor dispatch and JobHandle parent vocabulary
type: scenario
status: ratified
component: COMP-QMA-DAEMON
depends_on: [COMP-QMA-DAEMON, COMP-QMA-WIRE]
decisions: [DEC-0437, DEC-0439, DEC-0450]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/JOURNEYS.md, _docwork/workflows-increment-brief.md, _docwork/riders/workflows-construction-kit-2026-09-19.md, docs/decisions/ADR-0024-workflows-construction-kit.md, _docwork/gaps.yaml]
generated: 2026-09-19
verified: 2026-09-19
stale_after: 90d
---

# SCN-0021: Durable outbox successor dispatch and JobHandle parent vocabulary

This scenario pins J26/J27 durable workflow honesty: completing predecessor A and making successor B ready is one daemon-sqlite transaction plus outbox; a crash between A’s terminal write and B’s dispatch ack yields **at-least-once dispatch** and **exactly-once logical acceptance** of B under the receiver ledger (replay of the same `logical_invocation_id` returns the prior result); JobHandle reuses the QMA AD-17 parent vocabulary exactly; timeout / lost supervisor is `unknown`, never `aborted` or `failed`. [DEC-0439] [DEC-0437]

This document is a **specification of intended behavior**, not evidence that the code does this today. At `integration@270e992` TaskGraph classes exist but the store is in-memory with edges dropped and outbox absent (GAP-0095). [DEC-0450]

## Given

Task Graph persists `edges: {from, to, mapping}` in daemon sqlite (`task_graph_state`). Completing a predecessor and making successors ready is **one** sqlite transaction: (1) persist A terminal, (2) persist successor eligibility at a revision, (3) write an outbox row per newly ready successor. The dispatcher reads the outbox, invokes B with an AD-24 `InvocationEnvelope` carrying `logical_invocation_id`, and acks the outbox. No second scheduler. [DEC-0439] [DEC-0437]

Every public call carries `InvocationEnvelope` including `logical_invocation_id`, monotonic `attempt_id`, contribution tuple, `instance_id`, `config_revision`, `grant_id` snapshot, `effect_class`, `idempotency_key`, `reconcile_policy`, and `input_hash`. Effect-specific idempotency: `external-egress` MUST obtain a receipt or become `unknown` and MUST NOT blind-retry. [DEC-0437]

JobHandle reuses QMA AD-17 exactly: `queued` \| `running` \| `done` \| `failed` \| `cancelled` \| `aborted` \| `unknown`. Terminal = `done` / `failed` / `cancelled` / `aborted`. `unknown` is non-terminal and holds `environment_lease`. `awaiting_approval` is a Mission/Task gate, not a JobHandle state. Never `succeeded` on a handle. [DEC-0439]

## When

**(J27 — successor outbox after crash.)** Predecessor A completes with successor B eligible. The daemon crashes between A’s terminal write (and outbox row) and B’s dispatch ack. Restart replays unacked outbox rows. [DEC-0439]

**(J26 — uncertain external effect.)** An `external-egress` invocation’s acknowledgement is lost. The caller retries with the same `logical_invocation_id`. [DEC-0437] [DEC-0439]

**(Timeout.)** A supervisor times out or is lost while a job is outstanding. [DEC-0439]

## Then

**(1) Exactly-once logical acceptance of B.** Crash recovery replays unacked outbox rows (at-least-once dispatch). Receiver dedupe on `logical_invocation_id` returns the prior durable result, so B is accepted exactly once logically. [DEC-0439]

**(2) A-complete and B-ready are one transaction.** Terminal A, successor eligibility, and outbox row publish together. There is no window where A is terminal and B is silently forgotten without an outbox row. [DEC-0439]

**(3) Uncertain external effect stays unknown until reconcile.** State is `unknown` until reconcile; a second attempt with the same `logical_invocation_id` does not duplicate the order/export/message. Blind retry of `external-egress` is forbidden. [DEC-0437] [DEC-0439]

**(4) Timeout → unknown, not aborted.** Timeout / lost supervisor maps to JobHandle `unknown`, never `failed` or `aborted`. `cancelled` is explicit cancel; `aborted` is known environmental non-completion. [DEC-0439]

**(5) First durable terminal wins.** A cancel/complete race: the first durable terminal wins; later commands are no-ops recorded against that terminal. [DEC-0439]

**(6) Handle inventory.** Each handle records `logical_run_id`, `attempt_id`, and artifact inventory with completeness `complete` \| `partial` \| `missing` \| `expired`. [DEC-0439]

## Failure branches

**Branch A — duplicate successor on restart.** Restart dispatches a second logical B for the same outbox / `logical_invocation_id`. Forbidden: dispatch must be idempotent. [DEC-0439]

**Branch B — timeout labeled aborted or failed.** Supervisor timeout is recorded as `aborted` or `failed`. Forbidden: timeout/lost supervisor is `unknown`. [DEC-0439]

**Branch C — JobHandle gains succeeded / awaiting_approval.** Payload or API drifts to those states on a handle. Forbidden: parent vocab only; `awaiting_approval` stays a Mission/Task gate. [DEC-0439]

**Branch D — blind external-egress retry.** Lost acknowledgement is retried without receipt/reconcile, creating a duplicate side effect. Forbidden. [DEC-0437]

**Branch E — claiming outbox implemented at 270e992.** Treating this scenario as proof that durable edges/outbox exist. Forbidden: GAP-0095 / DEC-0450 record absence. [DEC-0450]

## Worked numbers

None. This is a registry-independent durability and identity scenario. The load-bearing chain is one transaction (A terminal + B eligibility + outbox) → crash → replay → one logical B; timeout → `unknown` (DEC-0439, DEC-0437).

GAP(GAP-0095): Task Graph edges and durable outbox are deferred; this scenario specifies the intended machine, not current store behavior.
