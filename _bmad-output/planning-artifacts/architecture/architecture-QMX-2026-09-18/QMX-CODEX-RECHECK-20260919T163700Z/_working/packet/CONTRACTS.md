---
name: Proposed public contracts
sitting: architecture-QMX-2026-09-18
status: proposed schemas — not minted CT ids; stage-c-reconciled
---

# Proposed contracts (representative payloads)

These are **design payloads**. They do not mint QMX persisted contract IDs. Owners and existing CTs stay as cited. Payloads below are **schema-complete** for the fields this sitting makes normative. They are not execution evidence.

Classification of each contract: `existing` (pinned implementation), `connect` (named store/API already in parent law), `amend`, `new`, `deferred`.

## 1. Operation descriptor (AD-3) — amend

```json
{
  "op_id": "qmb.analysis.project",
  "owner": "COMP-QMB",
  "version": 1,
  "input_schema": "qmb.analysis.project.v1",
  "output_shape": "artifact_ref",
  "cardinality": "one",
  "empty_policy": "refuse",
  "effect_class": "read",
  "occupancy": "query",
  "permission_requests": ["library.read"],
  "placement": "local-library",
  "refusal_family": "CT-04",
  "compatibility": { "qmb": ">=0.1" },
  "units": null,
  "progress": true,
  "lifecycle_verbs": ["start", "query-state", "cancel", "await"]
}
```

Closed `output_shape`: `value` | `artifact_ref` | `job_handle` | `event` | `stream`. Finite `event` ≠ persistent `stream`. Closed `effect_class`: `none` | `read` | `append-evidence` | `mutate-config` | `place-run` | `external-egress`. Closed `placement`: `local-library` | `daemon` | `worker` | `node`. Mapping is **not** on this descriptor (AD-5).

## 1b. Invocation envelope (AD-24) — new

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
  "idempotency_key": "inv:…:project",
  "reconcile_policy": "query-then-decide",
  "input_hash": "fp1:sha256:…"
}
```

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
  "resume_cursor": 41
}
```

`granted_ops` is GrantRecord ids, not bare op-id strings. `account_scope` is null unless granted. Current QMA `sess:` attachment is a **query**, not a durable field. `profile` is `ProductSessionProfile`, not `qma.core.ontology.Profile`.

CAS mutate:

```json
{
  "product_session_id": "psess:…",
  "expected_revision": 7,
  "command_id": "cmd:…",
  "payload": { "op": "select_ref", "ref": { "kind": "run", "id": "fp1:sha256:…" } }
}
```

Results: `ok` | `conflict` | `duplicate`. Reconnect is a query from `resume_cursor`; it does not re-issue unacked intent.

## 3b. GrantRecord (AD-24) — new

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
  "expires_at": "2026-12-31T00:00:00Z",
  "revoked_at": null
}
```

Immutable after mint. Upgrade cannot retarget. Intersection with host grants and health is AD-9.

## 4. Change request (AD-8, AD-29) — amend

```json
{
  "change_request_id": "cr:…",
  "from_session": "psess:…",
  "source_instance_id": "inst:…",
  "source_config_revision": 4,
  "context_revision": 7,
  "app_instance": { "package_id": "sector-intel", "version": "2.1.0" },
  "target_refs": ["fp1:sha256:…"],
  "base_hashes": ["fp1:sha256:…"],
  "request_hash": "fp1:sha256:…",
  "patch": { "kind": "filter_add", "path": "industry.known_at" },
  "validation": { "status": "valid", "conflicts": [] },
  "copied_private_memory": false,
  "apply_evidence": null
}
```

Lands in QMA staging; apply is operator/authoring — never `promote`, never app-use. Stale `base_hashes` → `conflict` / `rebase-required`.

## 5. Recipe definition and release (AD-12, AD-31) — amend / new

Definition (reviewable before a run):

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
      "revision": "…",
      "calendar": "FOREX",
      "timezone": "UTC",
      "units": "price",
      "adjustment": "none",
      "entitlement_ref": "cred:…",
      "licensing": "operator-owned"
    },
    {
      "kind": "ct10",
      "provider": "calendar-feed",
      "venue": null,
      "instrument": null,
      "revision": "…",
      "calendar": "NYSE",
      "timezone": "America/New_York",
      "units": "event",
      "adjustment": "none",
      "entitlement_ref": "cred:…",
      "licensing": "vendor-terms"
    }
  ],
  "transforms": [
    {
      "name": "asof-join",
      "known_at_policy": "no-lookahead",
      "alignment": "event-time",
      "missing_policy": "exclude",
      "late_policy": "label-late"
    }
  ],
  "split_policy": { "kind": "purged-kfold", "split_ref": null },
  "environment_pin": { "python": "3.14", "code_fp1": "fp1:sha256:…" },
  "output_schema": "derived.asof.v1",
  "completeness": "required"
}
```

Release (run result; Workbench AD-13):

```json
{
  "output_release": "fp1:sha256:…",
  "recipe_def_id": "rdef:…",
  "recipe_def_version": 3,
  "lineage": "CT-07",
  "completeness": "complete"
}
```

Not a Library kind. Display `recipe_id` is not identity. Provider ≠ venue.

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

States (parent law, not sitting dialect): `queued` | `running` | `done` | `failed` | `cancelled` | `aborted` | `unknown`. Terminal: `done` `failed` `cancelled` `aborted`. `unknown` is non-terminal and holds the lease. Timeout is never silent rejection and never `aborted`. `awaiting_approval` is a Mission/Task gate, not a JobHandle state. First durable terminal wins cancel/complete.

## 7. Stream subscription (AD-28) — amend

```json
{
  "sub_id": "sub:…",
  "channel": "ticks",
  "source_id": "dukascopy",
  "venue_id": null,
  "epoch": 3,
  "sequence": 1048291,
  "event_time": "2026-09-19T13:00:00.012Z",
  "receive_time": "2026-09-19T13:00:00.080Z",
  "phase": "replay",
  "cutover_watermark": { "epoch": 3, "sequence": 1100000 },
  "cursor": "3:1048291",
  "buffer_bound": 10000,
  "backpressure_policy": "block",
  "consumer_id": "psess:…",
  "refcount": 2,
  "shared": true
}
```

`source_id` is provider. `venue_id` is venue or null. Never a single `provider: ctrader-live` slot. Phase `replay` | `cutover` | `live`. Cancelling one consumer does not close a shared feed. Replay provenance cannot authorize a live command.

## 8. Pack manifest and lifecycle (AD-18, AD-30) — amend

```json
{
  "package_id": "sector-intel",
  "version": "2.1.0",
  "state": "enabled",
  "contributes": ["tool:inspect", "graph_template:daily-brief"],
  "requests": ["data.read", "library.read"],
  "compatibility": { "qma": ">=0.1", "qmb": ">=0.1" },
  "exports_secrets": false,
  "exports_transcripts": false,
  "migration": { "from": "2.0.0", "mode": "down" },
  "availability_revision": 12
}
```

`exports_secrets: false` is a request. Export oracle is an independent scanner report, not this field.

## 9. Graph Template topology (AD-6) — connect

Existing node/edge JSON plus **DAG** validation. Self-loop and any directed cycle refuse. Runtime Loop remains node state.

## 9b. Task outbox (AD-26) — connect / new

```json
{
  "outbox_id": "obx:…",
  "task_graph_id": "tg:…",
  "predecessor_node": "nA",
  "successor_node": "nB",
  "eligibility_revision": 5,
  "logical_invocation_id": "inv:…",
  "state": "pending"
}
```

`pending` → `dispatched` → `acked`. Restart replays `pending`/`dispatched` unacked. Exactly one logical successor effect.

## 9c. Join state (AD-26) — new

```json
{
  "join_id": "join:…",
  "mapping": "keyed-join",
  "expected_cardinality": 6,
  "duplicate_key_policy": "refuse",
  "watermark": "all-expected",
  "partitions": [
    { "partition_id": "k1", "status": "done", "logical_invocation_id": "inv:…" },
    { "partition_id": "k2", "status": "failed", "logical_invocation_id": "inv:…" }
  ]
}
```

Partial retry re-invokes only `failed` partitions. Late after watermark is `late`.

## 10. Deployment transition (AD-14, AD-25) — amend

```json
{
  "from_composition_fp": "fp1:sha256:…",
  "to_composition_fp": "fp1:sha256:…",
  "composition_class": "book-bms",
  "account_id": "acct:…",
  "venue_kind": "CTRADER",
  "command_owner_epoch": 18,
  "fencing_token": "fence:…",
  "state": "draining",
  "positions_snapshot": [{ "instrument": "EURUSD", "qty": "10000", "side": "buy" }],
  "orders_snapshot": [{ "external_id": "ord:…", "state": "unknown" }],
  "residual_disposition": "hold-manual",
  "predecessor_ack": false,
  "activation": "operator-second-act"
}
```

Closed `state`: `idle` | `drain-requested` | `draining` | `residuals-attributed` | `unknown-blocked` | `predecessor-acked` | `fenced-activate` | `active` | `retired`. Stale predecessor restart without current `(epoch, token)` is refused.

## 11. AlternativeRunConfig (AD-23) — new

```json
{
  "config_class": "alternative",
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
    "credential_ref": null
  },
  "admission": {
    "venue_touching": false,
    "paper_complete": false,
    "l17_promoted": false
  }
}
```

Book/BMS/bot keys **absent**. Dummy PolicyPair is `INVALID_INPUT`. Live requires sequential paper-then-live and `l17_promoted: true`. QML/QMB/MIS/QMN bind this config when it is the selected composition.

## 12. UngovernedWorkConfig vs ResolvedRunConfig — existing / amend

`ResolvedRunConfig` unchanged: `book_fp1`, `bms_fp1`, `bot_fp1` required. `UngovernedWorkConfig` omits those keys and is not ATC. Sensing-only is not a seat.

## 13. Checkpoint manifest (AD-27) — new

```json
{
  "checkpoint_id": "chk:…",
  "created_at": "2026-09-19T13:08:12Z",
  "owners": [
    { "owner": "COMP-QMF-DATA", "store": "rooms", "fence": "asof:…", "content_hash": "fp1:sha256:…" },
    { "owner": "COMP-QMB", "store": "jsonl", "fence": "ledger_seq:…", "content_hash": "fp1:sha256:…" },
    { "owner": "COMP-QML", "store": "research_root", "fence": "blob:…", "content_hash": "fp1:sha256:…" },
    { "owner": "artifacts", "store": "bytes", "fence": "fp1-set", "content_hash": "fp1:sha256:…" },
    { "owner": "COMP-QMA-DAEMON", "store": "sqlite", "fence": "journal_seq:…", "content_hash": "fp1:sha256:…" }
  ],
  "restore_order": ["COMP-QMF-DATA", "COMP-QMB", "COMP-QML", "artifacts", "COMP-QMA-DAEMON"]
}
```

Divergent store → quarantine `orphan`. Not a second evidence database.

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

| Owner | Library | qma-wire | qmb CLI | qma CLI | qmn CLI | node door |
|---|---|---|---|---|---|---|
| COMP-QMB | yes | via CT-47 | yes | absent | absent | via QMN unforked run_slice |
| COMP-QMA | yes | yes | only as QMB-owned orchestration of a QMB step | **absent** | absent | no |
| COMP-QMN | yes | evidence HTTP | no | absent | **absent** | yes |
| COMP-QML | yes | no | no | absent | absent | no |

Parity is semantic across **supported** doors. Unsupported → `unsupported_door`. QMB remains the only operator CLI.
