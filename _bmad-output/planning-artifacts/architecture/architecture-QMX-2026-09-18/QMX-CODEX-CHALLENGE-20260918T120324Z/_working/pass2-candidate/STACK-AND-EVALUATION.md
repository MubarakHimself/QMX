---
name: Stack, compatibility, and evaluation
sitting: architecture-QMX-2026-09-18
checked: 2026-09-18
---

# Stack and evaluation record

## Existing baseline (reuse)

| Layer | Choice | Evidence |
|---|---|---|
| Language | CPython 3.14 | `.python-version`; observed **3.14.6** at 270e992 |
| Packaging | uv workspace + lockfile | `docs/architecture/stack.md` |
| QMF stores | Parquet / DuckDB / SQLite / JSONL | DEC-0117 |
| QMA | asyncio daemon, sqlite single writer, qma-wire JSON-RPC vocabulary | ADR-0020 |
| QMB | library + CLI; Optuna 4.9.0 TPE | qmb/pyproject.toml |
| QMN | systemd VPS; three doors; no CLI | ADR-0019 |
| Schema | qmf-core fingerprint + typed refusals; no extra JSON Schema runtime required for V1 descriptors | AD-3 can be frozen dataclasses + CT-04 |

## Proposed changes (explicit)

| Change | Why | Migration |
|---|---|---|
| ContributionHit DTO on qma-wire | Capability discovery without new kinds | Additive CT-40 family (same pattern as federated discovery) |
| product_session tables in daemon sqlite | AD-8 durability | Named closed-store amendment; migrate with existing lifecycle |
| Persist task_graph_state | AD-7 continuation | Lifecycle already names the store; implement tables |
| DAG topology validator | Close A→B→C→A hole | Behaviour change at Graph Template register; existing 2-cycle tests stay |
| Role **label** Portfolio Manager | INT-25 | Display/docs/skills only; no slug rewrite |

No silent dependency upgrades. No pandas/numpy into qmf-core. No n8n/Hermes/OpenBB/LEAN import.

## Donor notes (2026-09-18 primary sources)

| Reference | Observed | QMX adaptation | Mismatch |
|---|---|---|---|
| Hermes plugins | Manifest / schema / handler split; capabilities as **consent not sandbox**; `dispatch_tool`; config vs state; some dep failures are warnings | Keep split; **fail-closed** missing deps | Do not copy full-trust portable plugins or warning-and-continue |
| Hermes desktop SDK | Separate desktop / dashboard / python plugin surfaces | Inform GAP-0081 contribution types | Not a VS Code ranking |
| n8n | Node descriptors, connections, subworkflows, draft vs published | Mental model for Board vs Template vs run | Source-available; do not embed |
| OpenBB | Provider fetchers + widgets.json / apps.json + shared params | Provider contract + mini-app declarations | Do not adopt OpenBB runtime |
| JSON Render v0.20.0 | Catalog-constrained generative UI | Inspectors/forms from registered components | Not domain execution; host stack unchosen |
| MCP Apps 2026-01-26 | Tool-linked sandboxed HTML | Optional copilot tool views | Not native navigation |
| mutmut | Fork required; Windows = WSL; `apply` writes mutants | Optional test-strength on disposable copies | Not a product dep |
| LSE (observed) | Catalogue→preview→builder; REST vs export job vs WS replay→live | Recipe + job + stream phases | Do not clone UI or paid jobs |
| Taskade (docs/public) | Apps over workspace assets | Mini-app as grouping | Signed-in workspace unverified |
| QuantConnect/LEAN | Provider vs broker split | Mental model only | DEC-0085: no donor engine |

## Testing plan (architecture, not executed suite)

1. **BDD journeys** in `JOURNEYS.md` — Stage B expands independently.
2. **Contract tests** for AD-3 descriptors and hit classes.
3. **State-machine tests** for job handles and product-session grants.
4. **Fault injection** for shared-stream cancel, UNKNOWN commands, partial sqlite.
5. **Mutation testing** later on isolated copies of QMB compile refusals and topology validator — WSL on this Windows host.
6. Preserve default Book/BMS regression (existing QMB/QMN tests) as the first gate of any alternative-system work.

Hypothesis (stateful) and Caliper remain optional later adapters. They are not pinned.
