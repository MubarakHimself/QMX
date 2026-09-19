---
name: Proposed public contracts
sitting: architecture-QMX-2026-09-18
status: proposed schemas — not minted CT ids; stage-c-reconciled; 2026-09-19 desk-fix after focused recheck
---

# Proposed contracts (representative payloads)

These are **design payloads**. They do not mint QMX persisted contract IDs. Owners and existing CTs stay as cited. Payloads below are **normative schemas for this sitting** after the 2026-09-19 focused recheck desk-fix. They still do not mint CT ids. They are not execution evidence.

Classification of each contract: `existing` (pinned implementation), `connect` (named store/API already in parent law), `amend`, `new`, `deferred`.

## 1. Operation descriptor (AD-3) — amend

Complete normative schema (RC-16). This is not a fragment.

```json
{
  "op_id": "qmb.analysis.project",
  "owner": "COMP-QMB",
  "version": 1,
  "input_schema": "qmb.analysis.project.v1",
  "output_shape": "artifact_ref",
  "input_cardinality": "one",
  "output_cardinality": "one",
  "empty_policy": "refuse",
  "configuration": {
    "defaults": { "as_of": null },
    "required_keys": ["run_fp1"],
    "optional_keys": ["as_of"]
  },
  "declared_operation_dependencies": [],
  "resource_needs": {
    "occupancy": "query",
    "memory_class": "light",
    "requires_environment": false
  },
  "documentation_refs": ["docs/components/qmb.md#analysis-project"],
  "validation_class": "schema+semantic",
  "units": null,
  "compatibility": { "qmb": ">=0.1" },
  "effect_class": "read",
  "permission_requests": ["library.read"],
  "placement": "local-library",
  "error_refusal_shape": {
    "family": "CT-04",
    "codes": ["INVALID_INPUT", "UNAVAILABLE", "UNSUPPORTED_DOOR", "STALE_OBSERVATION", "GRANT_MISMATCH"]
  },
  "progress": true,
  "lifecycle_verbs": ["start", "query-state", "cancel", "await"],
  "supported_doors": [
    { "adapter": "library", "door": "qmb.analysis.project" },
    { "adapter": "qmb-cli", "door": "qmb analysis project" },
    { "adapter": "qma-wire", "door": "via CT-47" }
  ]
}
```

Closed `output_shape`: `value` | `artifact_ref` | `job_handle` | `event` | `stream`. Finite `event` ≠ persistent `stream`. Closed `effect_class`: `none` | `read` | `append-evidence` | `mutate-config` | `place-run` | `external-egress`. Closed `placement`: `local-library` | `daemon` | `worker` | `node`. Closed cardinality: `one` | `many` for each of `input_cardinality` and `output_cardinality` (never a single merged `cardinality` field). Mapping is **not** on this descriptor (AD-5).

## 1b. Invocation envelope (AD-24) — new

The envelope is **signed/bound request context, not authority** (RC-03). On every hop the host MUST resolve the contribution/descriptor and `GrantRecord` from authoritative stores, compare every bound field below to those stores, and emit a typed `stale` / `mismatch` refusal before execution.

```json
{
  "logical_invocation_id": "inv:…",
  "attempt_id": 2,
  "op_id": "qmb.analysis.project",
  "op_version": 1,
  "contribution": { "qualified_id": "analysis-backtest:qmb", "package_version": "0.1.0" },
  "instance_id": "inst:…",
  "config_revision": 4,
  "caller_session_ref": "psess:…",
  "callee_session_ref": null,
  "grant_id": "grant:…",
  "effect_class": "read",
  "idempotency_key": "idem:…",
  "reconcile_policy": "query-then-decide",
  "input_hash": "fp1:sha256:…",
  "parent_logical_invocation_id": null,
  "call_depth": 0
}
```

**Idempotency (RC-04).** Issuer of `idempotency_key` is the **caller**. Uniqueness domain is `(principal, op_id, op_version, instance_id, config_revision, grant_id, target, canonical_input_hash)`. Minimum retention equals the journal lifetime of the invocation. Collision with a different payload hash → typed refusal. Replay of the same key within retention returns the prior result. Nested public calls MUST carry `parent_logical_invocation_id` and `call_depth`; child `logical_invocation_id` is derived deterministically from `(parent_logical_invocation_id, call_depth, child_op_id, child_canonical_input_hash)`.

**`input_hash` preimage** = canonical JSON of the `input_schema`-validated payload (sorted keys, no whitespace variance, schema-validated only — secrets never inlined).

Ambiguous `instance_id` / `config_revision` → typed refusal. `external-egress` without a receipt → `unknown`; never a blind second attempt.

## 2. Discovery hits (AD-2, AD-30) — existing two-class + new ContributionHit

Existing (source-inspected @ 270e992):

```json
{ "hit_class": "knowledge", "source_ref": "strats", "snapshot_ref": "fp1:sha256:…", "locator": "strategies/STRAT-000001-…/README.md" }
{ "hit_class": "artifact", "fp1": "fp1:sha256:…", "kind": "bot-definition" }
```

Proposed additive (named amendment of DEC-0389):

```json
{
  "hit_class": "contribution",
  "plugin_id": "analysis-backtest",
  "point": "tool",
  "qualified_id": "analysis-backtest:qmb",
  "package_id": "analysis-backtest",
  "package_version": "0.1.0",
  "availability_revision": 12,
  "availability": "enabled"
}
```

Pin stores `(qualified_id, package_version, availability_revision)`. Invoke after disable/uninstall returns `unavailable` or `tombstone`, never another version. Refused on this facade: `strats`, `qml_candidate`, hypothesis kinds.

## 3. Product session (AD-8, AD-29) — new / connect

```json
{
  "product_session_id": "psess:…",
  "profile": "app-use",
  "principal": "operator",
  "context_revision": 7,
  "app_instance_id": "inst:…",
  "granted_ops": ["grant:…"],
  "selected_refs": [{ "kind": "run", "id": "fp1:sha256:…" }],
  "account_scope": null,
  "resume_cursor": 41,
  "cursor_generation": 2
}
```

`granted_ops` is GrantRecord ids, not bare op-id strings. `account_scope` is null unless granted. Current QMA `sess:` attachment is a **query**, not a durable field. `profile` is `ProductSessionProfile`, not `qma.core.ontology.Profile`.

CAS mutate (RC-11):

```json
{
  "product_session_id": "psess:…",
  "expected_revision": 7,
  "command_id": "cmd:…",
  "payload": { "op": "select_ref", "ref": { "kind": "run", "id": "fp1:sha256:…" } },
  "payload_hash": "fp1:sha256:…"
}
```

**`command_id` namespace** = `(product_session_id, principal, command_id)`. Retention = session journal lifetime. Collision with a different `payload_hash` refuses. Results: `ok` | `conflict` | `duplicate` | `in_progress`. `duplicate` returns the prior durable result; `in_progress` returns the still-open attempt identity. Reconnect is a query from `(resume_cursor, cursor_generation)`; it does not re-issue unacked intent. When history is compacted past the cursor, the host returns a **snapshot/resync** response carrying the current projection and a new cursor generation — never a silent empty replay.

## 3b. GrantRecord (AD-24) — new

Minted grant is **immutable**. `revoked_at` is **not** a GrantRecord field (RC-05).

```json
{
  "grant_id": "grant:…",
  "principal": "operator",
  "audience": "psess:…",
  "contribution": { "qualified_id": "analysis-backtest:qmb", "package_version": "0.1.0" },
  "instance_id": "inst:…",
  "config_revision": 4,
  "op_id": "qmb.analysis.project",
  "op_version": 1,
  "effect_class": "read",
  "parameter_ceiling": { "allow_keys": ["run_fp1", "as_of"] },
  "account_scope": null,
  "expires_at": "2026-12-31T00:00:00Z"
}
```

### GrantRevocation (append-only; separate from GrantRecord)

```json
{
  "grant_id": "grant:…",
  "revoked_at": "2026-09-19T14:00:00Z",
  "principal": "operator",
  "reason": "session-ended"
}
```

**Evaluation moments:** accept, dispatch, nested call, retry, external commit. Already-accepted work may finish under the grant that accepted it. New dispatch after revoke (or after `expires_at`) is refused. Upgrade cannot retarget. Intersection with host grants and health is AD-9.

## 4. Change request (AD-8, AD-29) — amend

Three separate records (RC-12). App-use mints the request only.

### ChangeRequest (immutable)

```json
{
  "change_request_id": "cr:…",
  "from_session": "psess:…",
  "source_instance_id": "inst:…",
  "source_config_revision": 4,
  "context_revision": 7,
  "app_instance": { "package_id": "sector-intel", "version": "2.1.0" },
  "targets": [
    { "target_ref": "fp1:sha256:…", "base_hash": "fp1:sha256:…" }
  ],
  "request_hash": "fp1:sha256:…",
  "patch": { "kind": "filter_add", "path": "industry.known_at" },
  "copied_private_memory": false
}
```

**`request_hash` preimage** = canonical JSON over requester-controlled facts + patch only: `(change_request_id, from_session, source_instance_id, source_config_revision, context_revision, app_instance, targets, patch, copied_private_memory)`. No validation verdict and no apply evidence may enter the preimage.

### ChangeValidationRecord (validator authority)

```json
{
  "change_request_id": "cr:…",
  "request_hash": "fp1:sha256:…",
  "validator_principal": "authoring",
  "verdict": "valid",
  "conflicts": [],
  "validated_at": "2026-09-19T13:10:00Z"
}
```

Closed `verdict`: `conflict` | `rebase-required` | `valid`.

### ChangeApplyRecord (append-only)

```json
{
  "change_request_id": "cr:…",
  "request_hash": "fp1:sha256:…",
  "applied_base_hashes": ["fp1:sha256:…"],
  "result_hashes": ["fp1:sha256:…"],
  "authoring_principal": "authoring",
  "operator_principal": "operator",
  "applied_at": "2026-09-19T13:12:00Z",
  "outcome": "applied"
}
```

Lands in QMA staging; apply is operator/authoring — never `promote`, never app-use. Stale base hashes → `conflict` / `rebase-required` on the validation record.

## 5. Recipe definition and release (AD-12, AD-31) — amend / new

Definition (reviewable before a run). Every AD-31 field is present (RC-15).

```json
{
  "recipe_def_id": "rdef:…",
  "recipe_def_version": 3,
  "recipe_def_hash": "fp1:sha256:…",
  "inputs": [
    {
      "kind": "ct10",
      "provider": "dukascopy",
      "venue": null,
      "instrument": "EURUSD",
      "coverage": { "start": "2020-01-01", "end": "2026-09-01", "resolution": "1m" },
      "schema_roles": ["price", "bid", "ask"],
      "revision": "rev:dukascopy:EURUSD:2026-09-01",
      "calendar": "FOREX",
      "timezone": "UTC",
      "units": "price",
      "freshness": { "max_lag": "5m", "as_of_policy": "event-time" },
      "provenance": { "source_class": "vendor-tick", "lineage_kind": "CT-07" },
      "entitlement_ref": "cred:…",
      "licensing": "operator-owned",
      "adjustment": "none"
    },
    {
      "kind": "ct10",
      "provider": "calendar-feed",
      "venue": null,
      "instrument": null,
      "coverage": { "start": "2020-01-01", "end": "2026-09-01", "resolution": "event" },
      "schema_roles": ["event"],
      "revision": "rev:calendar-feed:NYSE:2026-09-01",
      "calendar": "NYSE",
      "timezone": "America/New_York",
      "units": "event",
      "freshness": { "max_lag": "1d", "as_of_policy": "event-time" },
      "provenance": { "source_class": "news-calendar", "lineage_kind": "CT-07" },
      "entitlement_ref": "cred:…",
      "licensing": "vendor-terms",
      "adjustment": "none"
    }
  ],
  "transforms": [
    {
      "name": "asof-join",
      "alignment": "event-time",
      "known_at_policy": "no-lookahead",
      "missing_policy": "exclude",
      "late_policy": "label-late",
      "adjustment": "none"
    }
  ],
  "split_policy": { "kind": "purged-kfold", "split_ref": null },
  "environment_pin": { "python": "3.14", "code_fp1": "fp1:sha256:…" },
  "output_schema": "derived.asof.v1",
  "output_completeness_enumeration": ["complete", "partial", "missing", "expired"],
  "completeness_required": "complete"
}
```

**Canonical `recipe_def_hash` inputs:** `(recipe_def_id, recipe_def_version, inputs[], transforms[], split_policy, environment_pin, output_schema, completeness_required)` after canonical JSON normalization. Display rename and runtime credential **values** are excluded. Credentials appear only as typed runtime refs (`entitlement_ref`), never as secret bytes in the definition.

Release (run result; Workbench AD-13):

```json
{
  "output_release": "fp1:sha256:…",
  "recipe_def_id": "rdef:…",
  "recipe_def_version": 3,
  "recipe_def_hash": "fp1:sha256:…",
  "run_id": "run:…",
  "input_revisions": [
    { "provider": "dukascopy", "revision": "rev:dukascopy:EURUSD:2026-09-01" },
    { "provider": "calendar-feed", "revision": "rev:calendar-feed:NYSE:2026-09-01" }
  ],
  "transform_pins": [{ "name": "asof-join", "known_at_policy": "no-lookahead" }],
  "environment_pin": { "python": "3.14", "code_fp1": "fp1:sha256:…" },
  "lineage": {
    "kind": "CT-07",
    "binds": ["recipe_def_hash", "input_revisions", "transform_pins", "environment_pin", "run_id"]
  },
  "completeness": "complete"
}
```

Release lineage binds definition id/version/hash, every concrete input revision, transform/environment/code pins, `run_id`, and completeness. Not a Library kind. Display `recipe_id` is not identity. Provider ≠ venue. Cheap-veto A5 absorbs this schema.

## 6. Job handle (QMA AD-17 restated; AD-26) — amend sitting drift

```json
{
  "job_id": "job:…",
  "logical_run_id": "inv:…",
  "attempt_id": 1,
  "op_id": "qmb.backtest.run",
  "state": "running",
  "occupying": true,
  "environment_ref": "env:…",
  "cancelable": true,
  "result_ref": null,
  "artifacts": [
    { "fp1": "fp1:sha256:…", "completeness": "partial", "expired": false }
  ],
  "receipt": null
}
```

States (parent law, not sitting dialect): `queued` | `running` | `done` | `failed` | `cancelled` | `aborted` | `unknown`. Terminal: `done` `failed` `cancelled` `aborted`. `unknown` is non-terminal and holds the lease. Timeout is never silent rejection and never `aborted`. `awaiting_approval` is a Mission/Task gate, not a JobHandle state. First durable terminal wins cancel/complete. Never `succeeded`.

## 7. Stream records (AD-28) — amend

Split into subscription, data events, and typed control/evidence events (RC-10).

### StreamSubscription

```json
{
  "sub_id": "sub:…",
  "channel": "ticks",
  "source_id": "dukascopy",
  "venue_id": null,
  "epoch": 3,
  "sequence_domain": "provider-channel",
  "phase": "replay",
  "cutover_watermark": { "epoch": 3, "sequence": 1100000 },
  "cursor": { "epoch": 3, "sequence": 1048291 },
  "cursor_durable": true,
  "buffer_bound": 10000,
  "backpressure_policy": "block",
  "shared": true,
  "leases": [
    {
      "lease_id": "lease:…",
      "consumer_id": "psess:…",
      "expires_at": "2026-09-19T13:05:00Z",
      "renewed_at": "2026-09-19T13:00:00Z"
    }
  ],
  "refcount": 1
}
```

`refcount` is **derived** from live (non-expired) leases — never a bare independently written counter. Lease expiry removes the lease; reconnect may mint a new lease or be refused under backpressure. `source_id` is provider. `venue_id` is venue or null. Never a single `provider: ctrader-live` slot. Phase `replay` | `cutover` | `live`. Cancelling one consumer releases its lease; a shared feed stays until live leases are empty. Replay provenance cannot authorize a live command. Missing watermark at cutover → typed refusal / hold in `cutover` until barrier ack.

### StreamDataEvent

```json
{
  "event_kind": "data",
  "sub_id": "sub:…",
  "epoch": 3,
  "sequence": 1048291,
  "event_time": "2026-09-19T13:00:00.012Z",
  "receive_time": "2026-09-19T13:00:00.080Z",
  "phase": "replay",
  "payload_ref": "fp1:sha256:…"
}
```

### Stream control / evidence events

Closed `event_kind`: `gap` | `duplicate` | `late` | `heartbeat` | `loss` | `cutover-ack` | `lease-expire`.

```json
{
  "event_kind": "gap",
  "sub_id": "sub:…",
  "epoch": 3,
  "from_sequence": 1048200,
  "to_sequence": 1048290,
  "detected_at": "2026-09-19T13:00:00.100Z"
}
```

```json
{
  "event_kind": "cutover-ack",
  "sub_id": "sub:…",
  "epoch": 3,
  "watermark": { "epoch": 3, "sequence": 1100000 },
  "acked_at": "2026-09-19T13:01:00Z"
}
```

Epoch reset starts a new sequence domain; prior sequences are not comparable across epochs. Cutover barrier requires `cutover-ack` before live phase. Reconnect/backpressure outcomes follow `backpressure_policy`: `block` | `disconnect` | `spill-with-evidence`.

## 8. Pack manifest and lifecycle (AD-18, AD-30) — amend

Manifest `contributes` MUST be `{point, local_id}` objects matching AD-2 (RC-13). Qualification to `qualified_id` is `package_id + ":" + local_id` (or the pack-declared qualification rule). Collision on `(point, qualified_id)` at enable refuses. Availability revision publication is atomic with roster swap.

```json
{
  "package_id": "sector-intel",
  "version": "2.1.0",
  "state": "enabled",
  "contributes": [
    { "point": "tool", "local_id": "inspect" },
    { "point": "graph_template", "local_id": "daily-brief" }
  ],
  "requests": ["data.read", "library.read"],
  "compatibility": { "qma": ">=0.1", "qmb": ">=0.1" },
  "exports_secrets": false,
  "exports_transcripts": false,
  "availability_revision": 12
}
```

`exports_secrets: false` is a request. Export oracle is an independent scanner report, not this field. Manifest exports_secrets is still not evidence.

### PackTransition (RC-14)

```json
{
  "package_id": "sector-intel",
  "from_state": "installed",
  "to_state": "validated",
  "roster_generation": 12,
  "cas_token": "roster:12",
  "transitioned_at": "2026-09-19T12:00:00Z",
  "principal": "operator"
}
```

Pack states: `downloaded` → `installed` → `validated` → `enabled` ⇄ `disabled` → `uninstalled`. Each transition is a CAS on `roster_generation`.

### Migration record

```json
{
  "package_id": "sector-intel",
  "from_version": "2.0.0",
  "to_version": "2.1.0",
  "mode": "down",
  "phase": "commit",
  "outcome": "ok",
  "recovery": null
}
```

Closed `phase`: `prepare` | `commit` | `rollback`. Closed `mode`: `down` | `forward_only`. Failed prepare/commit restores last usable roster, or records `recovery: "forward_only"` with operator confirmation.

### Dependant / pin leases

```json
{
  "package_id": "sector-intel",
  "version": "2.1.0",
  "dependants": ["miniapp:sector-board"],
  "pin_leases": [
    {
      "lease_id": "pinlease:…",
      "qualified_id": "sector-intel:inspect",
      "package_version": "2.1.0",
      "availability_revision": 12,
      "holder_invocation_id": "inv:…",
      "expires_at": null
    }
  ]
}
```

GC eligibility only when `pin_leases` is empty and no dependant remains. In-flight pinned runs keep the bytes they started with.

### ExportScanReport (versioned)

```json
{
  "report_version": 1,
  "package_id": "sector-intel",
  "package_version": "2.1.0",
  "threat_model": {
    "classes": ["secret_values", "private_paths", "transcripts"],
    "scope": "export-bundle"
  },
  "detectors": ["secret-regex-v3", "path-allowlist-v1", "transcript-marker-v1"],
  "coverage": { "files_scanned": 42, "bytes_scanned": 1048576, "complete": true },
  "findings": [
    { "class": "secret_values", "path": "config/local.yaml", "action": "rewrite" }
  ],
  "rewrite_map": [
    { "path": "config/local.yaml", "from_hash": "fp1:sha256:…", "to_ref": "cred:…", "to_hash": "fp1:sha256:…" }
  ],
  "post_rewrite_hash": "fp1:sha256:…",
  "post_rewrite_signature": "sig:…",
  "result": "fail-closed-pass"
}
```

Closed `result`: `fail-closed-pass` | `fail-closed-fail`. Incomplete coverage or unhandled finding → `fail-closed-fail`.

## 9. Graph Template topology (AD-6) — connect

Existing node/edge JSON plus **DAG** validation. Self-loop and any directed cycle refuse. Runtime Loop remains node state.

## 9b. Task outbox (AD-26) — connect / new

Unique key: `(graph_run_id, successor_node_id, predecessor_revision, partition_id)` (RC-07). Persist complete target + envelope hash.

```json
{
  "outbox_id": "obx:…",
  "graph_run_id": "tg:…",
  "successor_node_id": "nB",
  "predecessor_node_id": "nA",
  "predecessor_revision": 5,
  "partition_id": "k1",
  "logical_invocation_id": "inv:…",
  "target": {
    "op_id": "qmb.analysis.project",
    "op_version": 1,
    "instance_id": "inst:…",
    "config_revision": 4
  },
  "envelope_hash": "fp1:sha256:…",
  "transport_state": "pending",
  "acceptance_state": null,
  "effect_state": null,
  "receiver_acceptance_id": null
}
```

Closed `transport_state`: `pending` | `dispatched`. Closed `acceptance_state`: `accepted` (receiver durable). Closed `effect_state`: `effected` (logical completion). Distinguish **dispatched** (transport) vs **accepted** (receiver durable) vs **effected** (logical completion). Receiver dedupe is on `logical_invocation_id`; replay returns the prior result. At-least-once dispatch with exactly-once logical acceptance under the receiver ledger. The outbox alone does **not** prove “exactly one logical successor effect”; acceptance is proven by the receiver ledger.

## 9c. Join state (AD-26) — new

```json
{
  "join_id": "join:…",
  "graph_run_id": "tg:…",
  "node_id": "nJoin",
  "edge_id": "eA-Join",
  "definition_revision": 3,
  "join_revision": 1,
  "mapping": "keyed-join",
  "expected_cardinality": 6,
  "duplicate_key_policy": "first-wins",
  "first_wins_order": ["event_time", "receive_time", "source_event_id"],
  "watermark": {
    "kind": "all-expected",
    "cause": null,
    "closed_at": null
  },
  "partitions": [
    {
      "partition_id": "k1",
      "status": "done",
      "logical_invocation_id": "inv:…",
      "source_event_id": "sev:…",
      "event_time": "2026-09-19T12:00:00Z",
      "receive_time": "2026-09-19T12:00:00.050Z",
      "result_identity": "fp1:sha256:…"
    },
    {
      "partition_id": "k2",
      "status": "failed",
      "logical_invocation_id": "inv:…",
      "source_event_id": "sev:…",
      "event_time": "2026-09-19T12:00:01Z",
      "receive_time": "2026-09-19T12:00:01.040Z",
      "result_identity": null
    }
  ],
  "late_events": [
    {
      "source_event_id": "sev:late:…",
      "partition_id": "k1",
      "detected_at": "2026-09-19T12:05:00Z",
      "disposition": "late"
    }
  ]
}
```

`first-wins` total order is `(event_time, receive_time, source_event_id)` (RC-08). Persist watermark cause/time and late-event evidence. Partial retry uses the same join definition (`definition_revision` + `join_revision`) and reuses successful partition `result_identity` values.

## 10. Deployment transition (AD-14, AD-25) — amend

Fence key is `(account, venue, role)`. Deploy payload includes `role`, `attempt_id`, machine revision, issuer, timeout/escalation, predecessor ack, snapshot identities, completion evidence, CAS guards, token uniqueness (RC-06).

```json
{
  "from_composition_fp": "fp1:sha256:…",
  "to_composition_fp": "fp1:sha256:…",
  "composition_class": "book-bms",
  "account_id": "acct:…",
  "venue_kind": "CTRADER",
  "role": "pm",
  "command_owner_epoch": 18,
  "attempt_id": 1,
  "machine_revision": 3,
  "fencing_token": "fence:…",
  "token_unique_under": ["account_id", "venue_kind", "role", "command_owner_epoch"],
  "issuer": "COMP-QMN",
  "state": "draining",
  "positions_snapshot": [{ "instrument": "EURUSD", "qty": "10000", "side": "buy", "snapshot_id": "snap:pos:…" }],
  "orders_snapshot": [{ "external_id": "ord:…", "state": "unknown", "snapshot_id": "snap:ord:…" }],
  "residual_disposition": "hold-manual",
  "predecessor_ack": false,
  "timeout": { "drain_deadline": "2026-09-19T13:30:00Z", "escalation": "operator-page" },
  "cas_guard": { "expected_epoch": 18, "expected_token": "fence:…" },
  "completion_evidence": null,
  "activation": "operator-second-act"
}
```

**Ordered happy path:** `idle` → `drain-requested` → `draining` → `residuals-attributed` → `predecessor-acked` → `fenced-activate` → `active` → `retired`.

**Terminal branch (not a step that continues):** from `draining` (or residual attribution), `unknown-blocked` is a **terminal branch of this attempt**. It does not proceed to `predecessor-acked`. Operator reconcile mints a **new attempt/epoch** with immutable evidence — never an automatic retry. Stale predecessor restart without current `(epoch, token)` is refused. CAS guards refuse mismatched epoch/token.

## 11. AlternativeRunConfig (AD-23) — new

MUST carry `composition_fp` and a versioned immutable PolicyPair identity (RC-01). Inline policy bodies are snapshots, not sole identity. Selection, grants, simulation evidence, fencing, and CT-07 lineage bind to `composition_fp` + `policy_pair_hash`.

```json
{
  "config_class": "alternative",
  "composition_fp": "fp1:sha256:…",
  "policy_pair_id": "pp:kelly-v1",
  "policy_pair_version": 1,
  "policy_pair_hash": "fp1:sha256:…",
  "policy_pair": {
    "accounting": {
      "cash_identity": "internal-cash",
      "position_identity": "instrument+account",
      "fill_application": "fifo",
      "valuation": "last-mark",
      "currency": "USD",
      "residual_meaning": "open-qty"
    },
    "risk": {
      "max_gross": "100000",
      "halt": "on-unknown-or-limit",
      "sizing": "fixed-fraction",
      "override_principal": "operator"
    }
  },
  "command": {
    "account_id": "acct:…",
    "venue_kind": null,
    "role": "pm",
    "instrument": "EURUSD",
    "adapter_capability": "internal-simulate",
    "credential_ref": null,
    "command_owner_epoch": 18
  },
  "admission": {
    "verdict": "admitted_simulate",
    "checked_grant_ids": ["grant:…"],
    "health_evidence_ref": "health:…",
    "health_revision": 4,
    "paper_run_ref": null,
    "paper_evidence_ref": null,
    "l17_promote_ref": null,
    "evaluator_principal": "host",
    "decided_at": "2026-09-19T12:00:00Z",
    "observation_freshness": { "max_age": "30s", "observed_at": "2026-09-19T12:00:00Z" }
  }
}
```

**PolicyPair hash preimage (canonical):** accounting fields + risk fields above; no secrets. Identity is `{policy_pair_id, policy_pair_version, policy_pair_hash}`.

**Admission (RC-02)** is an **authoritative host result**, not client booleans: typed `verdict`, checked grant IDs, health evidence/revision, paper run/evidence refs, L17 promote ref, evaluator principal, decision time. Stale observations refuse. Closed live-facing verdicts include `admitted_simulate` | `admitted_paper` | `admitted_live` | `not_promoted` | `refused`. Live ATC without paper + L17 is `not_promoted`. Book/BMS/bot keys **absent**. Dummy PolicyPair is `INVALID_INPUT`. Sensing-only is not ATC. QMN remains the only `qmf-venue` importer. QML/QMB/MIS/QMN bind this config when it is the selected composition.

## 12. UngovernedWorkConfig vs ResolvedRunConfig — existing / amend

`ResolvedRunConfig` unchanged: `book_fp1`, `bms_fp1`, `bot_fp1` required. `UngovernedWorkConfig` omits those keys and is not ATC. Sensing-only is not a seat.

## 13. Checkpoint manifest (AD-27) — new

Full checkpoint protocol (RC-09). Cheap-veto A6 absorbs this.

```json
{
  "checkpoint_id": "chk:…",
  "generation": 7,
  "schema_version": 1,
  "created_at": "2026-09-19T13:08:12Z",
  "cut": {
    "protocol": "prepare-commit",
    "barrier_id": "barrier:…",
    "opened_at": "2026-09-19T13:08:00Z",
    "closed_at": "2026-09-19T13:08:12Z"
  },
  "owners": [
    {
      "owner": "COMP-QMF-DATA",
      "store": "rooms",
      "fence": "asof:…",
      "prepare": "committed",
      "content_hash": "fp1:sha256:…",
      "backup_object_ref": "bak:qmf:…",
      "backup_object_hash": "fp1:sha256:…"
    },
    {
      "owner": "COMP-QMB",
      "store": "jsonl",
      "fence": "ledger_seq:…",
      "prepare": "committed",
      "content_hash": "fp1:sha256:…",
      "backup_object_ref": "bak:qmb:…",
      "backup_object_hash": "fp1:sha256:…"
    },
    {
      "owner": "COMP-QML",
      "store": "research_root",
      "fence": "blob:…",
      "prepare": "committed",
      "content_hash": "fp1:sha256:…",
      "backup_object_ref": "bak:qml:…",
      "backup_object_hash": "fp1:sha256:…"
    },
    {
      "owner": "artifacts",
      "store": "bytes",
      "fence": "fp1-set",
      "prepare": "committed",
      "content_hash": "fp1:sha256:…",
      "backup_object_ref": "bak:art:…",
      "backup_object_hash": "fp1:sha256:…"
    },
    {
      "owner": "COMP-QMA-DAEMON",
      "store": "sqlite",
      "fence": "journal_seq:…",
      "prepare": "committed",
      "content_hash": "fp1:sha256:…",
      "backup_object_ref": "bak:qma:…",
      "backup_object_hash": "fp1:sha256:…"
    }
  ],
  "inventory": {
    "included": ["COMP-QMF-DATA", "COMP-QMB", "COMP-QML", "artifacts", "COMP-QMA-DAEMON"],
    "excluded": []
  },
  "bootstrap_copy": {
    "location": "checkpoint-bootstrap/chk:…/manifest.json",
    "content_hash": "fp1:sha256:…",
    "note": "Separately stored copy of this manifest; bootstrap authority is this copy, not restore-order position"
  },
  "restore_order": ["COMP-QMF-DATA", "COMP-QMB", "COMP-QML", "artifacts", "COMP-QMA-DAEMON"],
  "post_restore": {
    "reference_check": "required",
    "external_effect_reconcile_records": []
  }
}
```

Closed per-owner `prepare`: `prepare` | `commit` | `fail`. Writer crossing the cut is refused or fenced. **Data dependency restore order** remains QMF → QMB → QML → artifacts → QMA. **Bootstrap authority** is the separately stored manifest copy — not “QMA restores last so it cannot bootstrap.” After restore: reference check; missing/corrupt refs → quarantine `orphan`; external-effect reconcile records run; absence of acknowledgement is `unknown`, not proof of non-execution. Partial checkpoint creation recovers by failing the generation and retaining the prior committed generation.

## 14. UI presentation DTOs (AD-17) — new, non-authoritative

```json
{
  "view_id": "view:heatmap",
  "view_version": 1,
  "op_id": "sector-intel.inspect",
  "mount": "mounted",
  "parameter_binding": { "schema": "sector-intel.inspect.v1", "values": { "as_of": "2026-09-01" } },
  "snapshot_cursor": 9,
  "stale": false
}
```

Mount/dispose MUST NOT start or kill durable work. Stale snapshot refuses invoke. Catalog entry cannot add fields to `input_schema`. MCP App HTML cannot grant tools.

## 15. Headless door matrix (AD-21) — amend

Normative matrix is per `op_id` + version (RC-17), not per owner. Enumerate supported adapters/doors. Unsupported → typed `unsupported_door`. Event/progress/reconnect behavior is per operation (from the descriptor).

| op_id | version | Owner | supported adapters/doors | unsupported → | progress | reconnect |
|---|---|---|---|---|---|---|
| `qmb.analysis.project` | 1 | COMP-QMB | library; qmb CLI; qma-wire via CT-47 | `unsupported_door` | yes | N/A (finite) |
| `qmb.backtest.run` | 1 | COMP-QMB | library; qmb CLI; qma-wire via CT-47; QMN unforked run_slice | `unsupported_door` | yes (JobHandle) | query-state / await |
| `qma.procedure.start` | 1 | COMP-QMA | library; qma-wire | `unsupported_door` (no qma CLI; no qmn CLI; no node door) | yes | resume from cursor |
| `qmn.evidence.query` | 1 | COMP-QMN | library; evidence HTTP; node door | `unsupported_door` (no qmb CLI; no qma CLI; **no qmn CLI**) | no | reconnect query |
| `qml.research.browse` | 1 | COMP-QML | library | `unsupported_door` | no | N/A |

Parity is semantic across **supported** doors for that `op_id`. Owner-wide matrices are non-normative summaries only. QMB remains the only operator CLI. Two operations of one component may advertise different doors.
