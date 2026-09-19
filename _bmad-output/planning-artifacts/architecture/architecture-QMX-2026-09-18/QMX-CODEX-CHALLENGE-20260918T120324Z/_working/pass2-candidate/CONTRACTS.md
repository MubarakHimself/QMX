---
name: Proposed public contracts
sitting: architecture-QMX-2026-09-18
status: proposed schemas — not minted CT ids
---

# Proposed contracts (representative payloads)

These are **design payloads**. They do not mint QMX persisted contract IDs. Owners and existing CTs stay as cited.

## 1. Operation descriptor (AD-3)

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
  "refusal_family": "CT-04"
}
```

Output shapes: `value` | `artifact_ref` | `job_handle` | `stream`.

## 2. Discovery hits (AD-2)

Existing (source-inspected @ 270e992):

```json
{ "hit_class": "knowledge", "source_ref": "strats", "snapshot_ref": "fp1:sha256:…", "locator": "strategies/STRAT-000001-…/README.md" }
{ "hit_class": "artifact", "fp1": "fp1:sha256:…", "kind": "bot-definition" }
```

Proposed additive (named amendment of DEC-0389):

```json
{ "hit_class": "contribution", "plugin_id": "analysis-backtest", "point": "tool", "qualified_id": "analysis-backtest:qmb", "package_id": "analysis-backtest", "package_version": "0.1.0" }
```

Refused: `strats`, `qml_candidate`, hypothesis kinds on this facade.

## 3. Product session (AD-8)

```json
{
  "product_session_id": "psess:…",
  "profile": "app-use",
  "principal": "operator",
  "context_revision": 7,
  "app_instance_id": "inst:…",
  "granted_ops": ["sector-intel.inspect", "sector-intel.rerun_allowed_inputs"],
  "selected_refs": [{ "kind": "run", "id": "fp1:sha256:…" }],
  "account_scope": null
}
```

`account_scope` is null unless granted. Current QMA `sess:` attachment is a **query**, not a durable field. `profile` is `ProductSessionProfile`, not `qma.core.ontology.Profile`.

## 4. Change request (app-use → authoring)

```json
{
  "change_request_id": "cr:…",
  "from_session": "psess:…",
  "app_instance": { "package_id": "sector-intel", "version": "2.1.0" },
  "target_refs": ["fp1:sha256:…"],
  "request": "Allow a new filter on industry membership known-at",
  "copied_private_memory": false
}
```

Lands in QMA staging; apply is operator/authoring — never `promote`.

## 5. Data recipe (AD-12)

```json
{
  "recipe_id": "derived:…",
  "inputs": [
    { "kind": "ct10", "source": "dukascopy", "instrument": "EURUSD", "revision": "…" },
    { "kind": "ct10", "source": "calendar-feed", "revision": "…" }
  ],
  "transforms": [{ "name": "asof-join", "known_at_policy": "no-lookahead" }],
  "split_ref": "fp1:sha256:…",
  "output_release": "fp1:sha256:…"
}
```

Not a Library kind. Lineage via CT-07.

## 6. Job handle (already QMA/QMB; restated)

```json
{
  "job_id": "job:…",
  "op_id": "qmb.backtest.run",
  "state": "running",
  "occupying": true,
  "environment_ref": "env:…",
  "cancelable": true,
  "result_ref": null
}
```

States: `queued | running | awaiting_approval | succeeded | failed | cancelled | unknown`. Timeout is never a silent rejection.

## 7. Stream subscription

```json
{
  "sub_id": "sub:…",
  "channel": "ticks",
  "provider": "ctrader-live",
  "phase": "replay",
  "cursor": "…",
  "consumer_id": "psess:…",
  "shared": true
}
```

Phase `replay | live`. Cancelling one consumer does not close a shared feed.

## 8. Pack manifest (AD-18)

```json
{
  "package_id": "sector-intel",
  "version": "2.1.0",
  "contributes": ["tool:inspect", "graph_template:daily-brief", "view:heatmap"],
  "requests": ["data.read", "library.read"],
  "compatibility": { "qma": ">=0.1", "qmb": ">=0.1" },
  "exports_secrets": false,
  "exports_transcripts": false
}
```

## 9. Graph Template topology (AD-6)

Existing node/edge JSON plus **DAG** validation. Self-loop and any directed cycle refuse. Runtime Loop remains node state.

## 10. Deployment transition (AD-14)

```json
{
  "from_composition_fp": "fp1:sha256:…",
  "to_composition_fp": "fp1:sha256:…",
  "mode": "stopped-or-drained",
  "unknown_commands": [],
  "residual_positions": "attributed",
  "activation": "operator-second-act"
}
```
