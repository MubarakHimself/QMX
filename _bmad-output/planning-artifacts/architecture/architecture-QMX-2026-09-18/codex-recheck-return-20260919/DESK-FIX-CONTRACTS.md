# Desk-fix contracts map (RC-01..RC-17)

Sitting: `architecture-QMX-2026-09-18`. Date: 2026-09-19.  
Scope: `CONTRACTS.md` + `ARCHITECTURE-SPINE.md` (AD-2 contributes clause, AD-3, AD-23..AD-31).  
Not claimed: Codex ratification. No CT/COMP minted. No production Python edited. No Documentation Factory. No epics started. No git commit.

## RC → change

| RC | What changed |
|---|---|
| **RC-01** | `CONTRACTS.md` §11 `AlternativeRunConfig`: added `composition_fp`, `{policy_pair_id, policy_pair_version, policy_pair_hash}`, canonical preimage (accounting+risk, no secrets); inline bodies marked snapshots; bind note for selection/grants/evidence/fencing/CT-07. `ARCHITECTURE-SPINE.md` AD-23 rule updated to the same. |
| **RC-02** | `CONTRACTS.md` §11: `command.command_owner_epoch`; `admission` replaced client booleans with authoritative host result (typed verdict, grant IDs, health evidence/revision, paper refs, L17 promote ref, evaluator, time, freshness); stale refuse; live without paper+L17 = `not_promoted`. AD-23 rule updated. |
| **RC-03** | `CONTRACTS.md` §1b: envelope stated as signed/bound request context not authority; every-hop resolve+compare+typed stale/mismatch refusal. AD-24 rule updated. |
| **RC-04** | `CONTRACTS.md` §1b: idempotency issuer=caller; uniqueness domain; retention=journal lifetime; collision refuse; replay→prior; `parent_logical_invocation_id`/`call_depth`; deterministic child id; `input_hash` preimage. AD-24 rule updated. |
| **RC-05** | `CONTRACTS.md` §3b: removed `revoked_at` from `GrantRecord`; added append-only `GrantRevocation`; evaluation moments + accepted-may-finish / new-dispatch-refused. AD-24 rule updated. |
| **RC-06** | `CONTRACTS.md` §10: `role`, `attempt_id`, `machine_revision`, issuer, timeout/escalation, snapshot identities, CAS guards, token uniqueness; happy path vs terminal `unknown-blocked` branch; reconcile = new attempt/epoch. AD-25 rule updated. |
| **RC-07** | `CONTRACTS.md` §9b: unique key `(graph_run_id, successor_node_id, predecessor_revision, partition_id)`; target+envelope_hash; `dispatched`/`accepted`/`effected`; receiver dedupe on `logical_invocation_id`; at-least-once dispatch / exactly-once acceptance under receiver ledger. AD-26 rule updated. |
| **RC-08** | `CONTRACTS.md` §9c: bind graph_run/node/edge/definition_revision/join_revision/source_event_id; `first-wins` order `(event_time, receive_time, source_event_id)`; watermark cause/time; late evidence; partial retry reuses result identities. AD-26 rule updated. |
| **RC-09** | `CONTRACTS.md` §13: generation, schema_version, cut/barrier, per-owner prepare\|commit\|fail, backup refs+hashes, inventory, bootstrap copy location, writer-crossing refuse/fence, post-restore reference check + external-effect reconcile; restore order kept as data dependency; bootstrap authority = separate manifest copy. AD-27 rule updated; A6 absorbs. |
| **RC-10** | `CONTRACTS.md` §7: split `StreamSubscription` / `StreamDataEvent` / control events; epoch reset, sequence domain, cutover-ack, missing-watermark, durable cursor, lease identities+expiry, derived refcount, reconnect/backpressure. AD-28 rule updated. |
| **RC-11** | `CONTRACTS.md` §3: `command_id` namespace `(product_session_id, principal, command_id)`; retention; payload_hash collision refuse; `in_progress`; cursor_generation; snapshot/resync. AD-29 rule updated. |
| **RC-12** | `CONTRACTS.md` §4: split immutable `ChangeRequest` (paired targets, request_hash preimage), `ChangeValidationRecord`, append-only `ChangeApplyRecord`; app-use mints request only. AD-29 rule updated. |
| **RC-13** | `CONTRACTS.md` §8: `contributes` as `{point, local_id}` objects; qualification; collision refuse; atomic availability_revision. AD-2 contributes clause + AD-30 rule updated. |
| **RC-14** | `CONTRACTS.md` §8: `PackTransition` CAS/roster_generation; migration prepare/commit/rollback\|forward_only; dependants + pin leases; GC only when no lease; versioned `ExportScanReport` (threat model, detectors, coverage, findings, rewrite map, post-rewrite hash/signature, fail-closed). AD-30 rule updated. |
| **RC-15** | `CONTRACTS.md` §5: full AD-31 field catalogue on definition; completeness enumeration; canonical hash inputs; credentials as typed refs; release lineage binds def id/version/hash, input revisions, pins, run_id, completeness. AD-31 rule updated; A5 absorbs. |
| **RC-16** | `CONTRACTS.md` header: “schema-complete” → normative schemas for this sitting / no CT mint / not execution evidence. §1: complete descriptor with `input_cardinality`/`output_cardinality`, configuration/defaults, deps, resources, docs refs, validation class, full error/refusal shape, supported_doors. AD-3 rule updated. |
| **RC-17** | `CONTRACTS.md` §15: per-`op_id`+version door matrix with adapters, typed `unsupported_door`, progress/reconnect per operation. (AD-21 already stated per-`op_id`; left unrenumbered.) Descriptor §1 also carries `supported_doors`. |

## Standing constraints preserved

- JobHandle vocab: `queued|running|done|failed|cancelled|aborted|unknown` (never `succeeded` / `awaiting_approval`).
- Dummy Book / incomplete PolicyPair → `INVALID_INPUT`.
- Sensing is not ATC; QMN sole venue importer.
- OD-01 CLOSED (stated in AD-23).
- Pass-I 85 IDs untouched.

## Remaining GAP / deferred (explicit)

These are **outside this desk-fix file pair** or left as non-architecture implementation choices — not silent omissions of RC behavior:

1. **GAP-DESK-DOCS-DRIFT** — **closed by orchestrator 2026-09-19:** ADR-0024 recheck-ran/not-approved; SCN-0019 three-record split; SCN-0020 owner COMP-QMB; SCN-0021 at-least-once dispatch / exactly-once acceptance; SCN-0022 bounded ExportScanReport; CHALLENGE-RECONCILIATION / CONFLICT-REGISTER / REQUIREMENTS-ADDENDUM OD-01 stale text removed. AF-01..AF-19 remain specification dispositions against the repaired text; they are not implementation closure.
2. **GAP-DESK-ENVELOPE-CRYPTO** — Envelope is contractually “signed/bound request context”; concrete signature algorithm / key hierarchy is an implementation choice not selected this sitting (behavior of mismatch refuse is specified).
3. **GAP-DESK-QUALIFY-FORMULA** — Default qualification stated as `package_id + ":" + local_id` (or pack-declared rule). Packs that need a different rule must declare it in manifest; no further formula minted.
4. **No Codex re-ratification** — disposition remains repairs-applied-on-desk, not ratified. A focused consistency recheck may follow; this file does not claim AF closure.
